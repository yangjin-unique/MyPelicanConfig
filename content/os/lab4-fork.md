Title: lab4:MultiProcessor支持、fork实现
Date: 2014-5-1
Category: os
Tags: Multi-processor, fork, Copy-on-Write, Syscall
Author: jin


###一、多核启动
lab4将JOS扩展到多核上，让JOS支持SMP（symmetric multiprocessing，一个multiprocessor模型）。
关于multiprocessor与multicore的区别请看：https://software.intel.com/en-us/blogs/2008/04/17/the-difference-between-multi-core-and-multi-processing。
multiprocessor（multiCPUS）中每个cpu属于不同的chip，然后插在同一个主板上，cpu之前通过总线通信；而multicore是所有cpus都在同一个chip上，这样cpu之间的通信时延更低，更省电；
在SMP系统中，正常运行时所有cpu功能一样，但在启动时，cpu分为两类：
1）Bootstrap processor（BSP）：负责初始化并启动系统；
2）Application processors（AP）：os启动后被BSP激活。

在SMP系统中，每个cpu有一个APIC（LAPIC：高级可编程中断管理器）单元，专门负责传送中断信号，见kern/lapic.c，LAPIC给每个cpu分配一个唯一的ID，需要用到的LAPIC的功能：
1）读取LAPIC的ID，指出当前代码运行在哪个cpu上（cpunum）；
2）从BSP发出STARTUP中断信号（IPI）给其他APs，以bringup这些AP；
3）控制LAPIC内部的定时器，以产生时钟中断来支持多任务抢占式调度。

cpu采用MMIO（memory mapped IO）访问其LAPIC。每个AP启动时都是先进入实时模式，BSP执行boot_aps时会将mpentry.S代码拷贝到MPENTRY_PADDR处（mpentry.S与boot.S比较相似，但不使能A20地址总线），并调用lapic_startap来启动其他每个AP，AP的启动路线为：
mpentry.S --> mp_main()
per-CPU相关数据：
1）per-CPU kernel stack：需要完成相应的映射；
2）per-CPU TSS和TSS描述符：每个cpu需要一个task state segment，来保存每个cpu内核栈的地址，TSS值为cpus[i].cpu_ts；
3）per-CPU 当前进程指针：执行当前cpu运行的进程，thiscpu->cpu_env，或者cpus[cpunum()]；
4）per-CPU系统寄存器：每个cpu有自己的寄存器；

Ex1-3：
1）完成BSP为其他AP创建各个cpu内核栈的映射；
2）建立perCPU的TSS；
上面任务较为简单，只是在给每个cpu建立TSS时要注意使用该cpu的tss。

###二、内核锁
为了保证多个cpu保存同步（执行内核代码时），jos采用一个big kernel lock：kernel_lock。
ex5完成以下任务，比较简单：
In i386_init(), acquire the lock before the BSP wakes up the other CPUs.
In mp_main(), acquire the lock after initializing the AP, and then call sched_yield() to start running environments on this AP.
In trap(), acquire the lock when trapped from user mode. To determine whether a trap happened in user mode or in kernel mode, check the low bits of the tf_cs.
In env_run(), release the lock right before switching to user mode. Do not do that too early or too late, otherwise you will experience races or deadlocks.

###三、Round-robin调度
创建3或更多的用户进程，然后让所有cpu去执行这些进程，需要在sched_yield中实现用户进程RR调度算法，算法本身并不复杂，但是实现的时候有几个点要考虑：
1）当curenv为null时，我开始没考虑到这个问题，运行时老是出现kernel page fault错误，最后调试看到curenv为null，也就是每个cpu最开始执行（boot完后）第一个进程时，此时应该从0开始选一个runable的进程；

###四、fork实现
前面创建的进程都是由内核自己创建的，现在要实现由用户进程来创建子进程，也就是unix下的fork系统调用。需要实现几个API：
sys_exofork:
This system call creates a new environment with an almost blank slate: nothing is mapped in the user portion of its address space, and it is not runnable. The new environment will have the same register state as the parent environment at the time of the sys_exofork call. In the parent, sys_exofork will return the envid_t of the newly created environment (or a negative error code if the environment allocation failed). In the child, however, it will return 0. (Since the child starts out marked as not runnable, sys_exofork will not actually return in the child until the parent has explicitly allowed this by marking the child runnable using....)
sys_env_set_status:
Sets the status of a specified environment to ENV_RUNNABLE or ENV_NOT_RUNNABLE. This system call is typically used to mark a new environment ready to run, once its address space and register state has been fully initialized.
sys_page_alloc:
Allocates a page of physical memory and maps it at a given virtual address in a given environment's address space.
sys_page_map:
Copy a page mapping (not the contents of a page!) from one environment's address space to another, leaving a memory sharing arrangement in place so that the new and the old mappings both refer to the same page of physical memory.
sys_page_unmap:
Unmap a page mapped at a given virtual address in a given environment.
这里要注意sys_exofork的实现，为了保证子进程返回0，父进程返回子进程id，在复制父进程
当前寄存器状态TrapFrame时，需要将子进程的trapframe的eax寄存器设为0，这样就保证了子进程的fork返回0（系统调用参数返回是通过寄存器eax）。其中fork实现如下：

    :::c
    sys_exofork(void)
    {
        struct Env *new_env = NULL;
        int ret;

        assert(curenv);
        if ((ret = env_alloc(&new_env, curenv->env_id)) < 0)
            return ret;
        new_env->env_status = ENV_NOT_RUNNABLE;
        memcpy(&new_env->env_tf, &curenv->env_tf, sizeof(struct Trapframe));
        new_env->env_tf.tf_regs.reg_eax = 0; //child process return 0
        return new_env->env_id;
    }

sys_exofork将父进程的状态（所有的相关寄存器，curenv->env_tf，这是TrapFrame，保存进程当前的状态信息）全部拷贝到子进程，然后将子进程的env_tf.tf_regs.reg_eax设为0，因为子进程的返回值就是通过这个来设置的。
除了父进程的状态信息，还需要将父进程的地址空间拷贝给子进程，那这个是在哪里实现的呢？
JOS是在用户态通过系统调用来实现的，在lib/dumpfork.c中完成地址空间的拷贝，

###五、Copy-on-Wirte fork实现
上面的fork实现中，最耗cpu的地方是要完全复制父进程的地址空间，包括复制每一个page的内容。而一般fork完后都是会去执行exec，所以出现了copy-on-write的方式来提高fork的性能，这也是unix下的实现方式，实际就是复制时我只是复制地址空间映射，也就是此时父子进程地址空间映射到同一块物理内存，然后将这块共享内存设为只读，当父子进程的任何一个想写这块内存时，会产生一个page fault。
JOS的将copy-on-wirte的fork实现在用户空间。

####1）User level page fault handler
通过系统调用sys_env_set_pgfault_upcall 来实现，当用户态出现page fault时，内核会重启这个进程，并让这个进程执行这个user page fault handler，并且使用的栈不是原进程的栈，而是叫user exception stack。要实现这一点，我们需要实现一个栈切换的机制，这个机制就像x86在用户态切换到内核态所完成的操作一样：设置trap frame（尤其是TrapFrame中有些是x86硬件完成的，这里我们需要自己来完成，使用结构UTrapFrame）。
user exception stack大小为一页，地址为[UXSTACKTOP-PGSIZE, UXSTACKTOP-1]。

####2）触发User level page fault handler
当user level page fault发生时，page_fault_handler会被调用，在这个里面，我们需要完成设置好user exception stack的内容（设置好struct UTrapFrame，UTrapFrame实际上保存在user exception stack的开始处）：

    :::c
    struct UTrapframe {
        /* information about the fault */
        uint32_t utf_fault_va;    /* va for T_PGFLT, 0 otherwise */
        uint32_t utf_err;
        /* trap-time return state */
        struct PushRegs utf_regs;
        uintptr_t utf_eip;
        uint32_t utf_eflags;
        /* the trap-time stack to return to */
        uintptr_t utf_esp;
    } __attribute__((packed));

UTrapframe 后面4个值是为了在exception stack上执行完user page fault handler时，能返回到用户进程发生trap的地方继续执行（注意是直接返回，不会再进入kernel）。刚进入user page fault handler时，exception stack结构如下（也就是UTrapFrame结构）：


                        <-- UXSTACKTOP
    trap-time esp
    trap-time eflags
    trap-time eip
    trap-time eax       start of struct PushRegs
    trap-time ecx
    trap-time edx
    trap-time ebx
    trap-time esp
    trap-time ebp
    trap-time esi
    trap-time edi       end of struct PushRegs
    tf_err (error code)
    fault_va            <-- %esp when handler is run

####3）user page fault handler入口
user page fault handler的入口在lib/pfentry.S中：
    
    .text
    .globl _pgfault_upcall
    _pgfault_upcall:
        // Call the C page fault handler.
        pushl %esp            // function argument: pointer to UTF
        movl _pgfault_handler, %eax
        call *%eax
        addl $4, %esp            // pop function argument
       //LAB 4
        movl 48(%esp), %eax
        subl $4, %eax
        movl %eax, 48(%esp)
        movl 40(%esp), %ebx
        movl %ebx, (%eax)
        // Restore the trap-time registers.  After you do this, you
        // can no longer modify any general-purpose registers.
        // LAB 4: Your code here.
        add $8, %esp
        popal
        // Restore eflags from the stack.  After you do this, you can
        // no longer use arithmetic operations or anything else that
        // modifies eflags.
        // LAB 4: Your code here.
        add $4, %esp
        popf
        // Switch back to the adjusted trap-time stack.
        // LAB 4: Your code here.
        popl %esp
        // Return to re-execute the instruction that faulted.
        // LAB 4: Your code here.
        ret
上面执行完user page fault handler后，要处理的问题是返回之前的用户进程，实现这个需要做两件事：一是切换到进程的原来的栈，二是装入进程的eip。
####4）fork实现
前面的几个步骤都是为了这个fork的实现，具体如下：
父进程将pgfault作为user level page fault handler；
父进程调用sys_exofork来创建子进程；
父进程调用duppage将copy-on-wirte的页映射到子进程的地址空间，同时也要重新remap这些页到自己的地址空间，并设为copy-on-write，同时把对应的PTEs设为可读。注意异常栈是不能这样做映射的。
父进程替子进程设置user page fault entrypoint；
父进程将子进程设为RUNNABLE，以便调度器调度运行。
当父子进程任意一个要写copy-on-write页时，会产生一个page fault，流程如下：
内核将这个page fault传递给_pgfault_upcall，_pgfault_upcall调用fork的pgfault handler；
pgfault检测这个fault是否是一次写（检测error code的FEC_WR位），还检测相应的PTE是否标志位PT_COW；如果不是，则panic；
pgfault分配一个新页，并映射到一个临时地址，然后将错误页的内容拷贝这个新页。最后将这个新页映射到相应的地址，读写权限，替代原来的映射；
贴上fork的代码：

    :::c
    static void
    pgfault(struct UTrapframe *utf)
    {
        void *addr = (void *) utf->utf_fault_va;
        uint32_t err = utf->utf_err;
        int r;

        // Check that the faulting access was (1) a write, and (2) to a
        // copy-on-write page.  If not, panic.
        // Hint:
        //   Use the read-only page table mappings at uvpt
        //   (see <inc/memlayout.h>).

        // LAB 4: Your code here.
        if ((err & FEC_WR) != FEC_WR)
            panic("pgfault: not write");

        uintptr_t fault_va = ROUNDDOWN((uintptr_t) addr, PGSIZE);
        pte_t pte = uvpt[PGNUM(fault_va)];
        if(!(pte & PTE_P) || !(pte & PTE_COW))
            panic("pgfault\n");
        // Allocate a new page, map it at a temporary location (PFTEMP),
        // copy the data from the old page to the new page, then move the new
        // page to the old page's address.
        // Hint:
        //   You should make three system calls.

        // LAB 4: Your code here.
        struct Page *p;
        envid_t envid = sys_getenvid();

        if((r = sys_page_alloc(envid, (void *) PFTEMP, PTE_P|PTE_U|PTE_W)) < 0)
            panic("pgfault handler error: %e\n", r);

        memmove((void *) PFTEMP, (void *) fault_va, PGSIZE);

        if((r = sys_page_map(envid, (void *) PFTEMP, envid,  (void *) fault_va, PTE_P|PTE_U|PTE_W)) < 0)
            panic("pgfault handler error: %e\n", r);
        sys_page_unmap(envid, (void *) PFTEMP);
    }

    //
    // Map our virtual page pn (address pn*PGSIZE) into the target envid
    // at the same virtual address.  If the page is writable or copy-on-write,
    // the new mapping must be created copy-on-write, and then our mapping must be
    // marked copy-on-write as well.  (Exercise: Why do we need to mark ours
    // copy-on-write again if it was already copy-on-write at the beginning of
    // this function?)
    //
    // Returns: 0 on success, < 0 on error.
    // It is also OK to panic on error.
    //
    static int
    duppage(envid_t envid, unsigned pn)
    {
        int r;

        // LAB 4: Your code here.
        envid_t cur_evid = sys_getenvid();
        pte_t pte = uvpt[pn];
        uint32_t perm = pte & PTE_SYSCALL;
        if((perm & PTE_W) || (perm & PTE_COW)){
            perm &= ~PTE_W;		
            perm |= PTE_COW;
        }

        if((r = sys_page_map(cur_evid, (void *) (pn*PGSIZE), 
            envid, (void *) (pn*PGSIZE), perm)) < 0) {
            panic("ken: duppage map error, %e, pn=%d\n", r, pn);
            return r;
        }
        
        if(perm & PTE_COW)
            if((r = sys_page_map(cur_evid, (void *) (pn*PGSIZE), 
                cur_evid, (void *) (pn*PGSIZE), perm)) < 0) {
                panic("ken: duppage map error1 %e\n", r);
                return r;
            }
        return 0;
    }

    //
    // User-level fork with copy-on-write.
    // Set up our page fault handler appropriately.
    // Create a child.
    // Copy our address space and page fault handler setup to the child.
    // Then mark the child as runnable and return.
    //
    // Returns: child's envid to the parent, 0 to the child, < 0 on error.
    // It is also OK to panic on error.
    //
    // Hint:
    //   Use uvpd, uvpt, and duppage.
    //   Remember to fix "thisenv" in the child process.
    //   Neither user exception stack should ever be marked copy-on-write,
    //   so you must allocate a new page for the child's user exception stack.
    //
    envid_t
    fork(void)
    {
        // LAB 4: Your code here.
        set_pgfault_handler(&pgfault); 
        envid_t child = sys_exofork();
        if(child < 0)
            return child;

        if(child == 0){
            thisenv = &envs[ENVX(sys_getenvid())];
            return 0;
        }

        uintptr_t addr = 0;
        int r;
        for(; addr < UXSTACKTOP - PGSIZE; addr += PGSIZE){
            if((uvpd[PDX(addr)] & PTE_P) && (uvpt[PGNUM(addr)] & PTE_P))
                if((r = duppage(child, PGNUM(addr))) < 0) {
                    cprintf("fork: duppage failed, addr=%x\n", addr);
                    return 0;		
                }
        }

        /* alloc exception stack for child process */
        if((r = sys_page_alloc(child, 
            (void *) UXSTACKTOP-PGSIZE, PTE_P|PTE_U|PTE_W)) < 0)
            return r;

        /* set user page fault handler for child process */
        extern void _pgfault_upcall(void *);
        if ((r = sys_env_set_pgfault_upcall(child, _pgfault_upcall)) < 0) {
            panic("fork: sys_env_set_upcall failed: %e\n", r);
            return r;
        }

        /* set child to RUNNABLE */
        if((r = sys_env_set_status(child, ENV_RUNNABLE)) < 0)
            return r;

        return child;
    }

