Title: lab3: Interrupts, Exceptions, Traps, Syscall
Date: 2014-4-1
Category: os
Tags: os, interrupts, exceptions, traps, syscall, task swtich
Author: jin



x86有两种类型的中断：

中断interrupt：主要指外设的中断；
异常exception：包括faults，traps，aborts，还有软中断（注意软中断也被当做异常处理）；
x86使用下面两种机制来实现中断处理机制。

####1. 中断描述符表IDT
x86允许256个中断，每个中断有一个中断向量interrupt vector，这个vector值在[0, 255]之间。当中断发生时，cpu使用这个vector来索引IDT，IDT与GDT类似，IDT中每一项都是一个描述符，叫IDT descriptors，有三种类型：
task gates：用于hardware支持的任务切换；
interrupt gates；
trap gates；
每个描述符长为8字节，结构如下（由于task gate没用到，就不说了）：


那么中断的过程如下图：

当中断产生时，cpu使用vector来索引IDT，找到相应的描述符，从描述符中获取下面的东西：
将描述符里面值赋给eip，也就是将eip指向了中断处理服务例程的指令（就是讲上上面的图中selector和offset组成得到eip）；
将描述符里面的值赋给cs寄存器，包括特权级DPL，一般中断处理这个都为0，内核态处理；


####2. 任务状态段TSS：task state segment
中断发生时，需要从当前任务中切换到中断模式，所以内核需要将当前任务环境存在某个地方以方便中断返回后继续执行当前任务。cpu会将当前任务环境（包括cs和eip等）保存到内核栈，内核利用这个TSS来实现这个，TSS是JOS内核自己定义的全局变量，然后在GDR中初始化TSS段描述符（属于task segment：GD_TSS0）：
    
    :::c 
    static  struct  Taskstate  ts;
    // Task state segment format (as described by the Pentium architecture book)
    struct Taskstate {
        uint32_t ts_link;    // Old ts selector
        uintptr_t ts_esp0;    // Stack pointers and segment selectors
        uint16_t ts_ss0;    //   after an increase in privilege level
        uint16_t ts_padding1;
        uintptr_t ts_esp1;
        uint16_t ts_ss1;
        uint16_t ts_padding2;
        uintptr_t ts_esp2;
        uint16_t ts_ss2;
        uint16_t ts_padding3;
        physaddr_t ts_cr3;    // Page directory base
        uintptr_t ts_eip;    // Saved state from last task switch
        uint32_t ts_eflags;
        uint32_t ts_eax;    // More saved state (registers)
        uint32_t ts_ecx;
        uint32_t ts_edx;
        uint32_t ts_ebx;
        uintptr_t ts_esp;
        uintptr_t ts_ebp;
        uint32_t ts_esi;
        uint32_t ts_edi;
        uint16_t ts_es;        // Even more saved state (segment selectors)
        uint16_t ts_padding4;
        uint16_t ts_cs;
        uint16_t ts_padding5;
        uint16_t ts_ss;
        uint16_t ts_padding6;
        uint16_t ts_ds;
        uint16_t ts_padding7;
        uint16_t ts_fs;
        uint16_t ts_padding8;
        uint16_t ts_gs;
        uint16_t ts_padding9;
        uint16_t ts_ldt;
        uint16_t ts_padding10;
        uint16_t ts_t;        // Trap on task switch
        uint16_t ts_iomb;    // I/O map base address
    };


当内核发生中断从用户模式切入到内核模式时，cpu如何找到内核栈？这个内核中的地址定义在TSS中（ts_esp0，这个在trap_init_percpu中初始化），cpu将当前任务的：ss，esp，eflags，cs，eip，可能还有error code推入到内核栈，然后再从IDT描述符中装载新的cs和eip，同时将esp和ss设置为这个内核栈，目前JOS只使用TSS中的这两个值。

举个例子：
假设cpu正在执行用户进程，并且执行了一个除0操作，将会发生如下过程：
cpu切换到TSS中ss0和esp0指定栈，对于JOS，就是GD_KD和KSTACKTOP；
cpu将下面值入栈：


                     +--------------------+ KSTACKTOP             
                     | 0x00000 | old SS   |     " - 4
                     |      old ESP       |     " - 8
                     |     old EFLAGS     |     " - 12
                     | 0x00000 | old CS   |     " - 16
                     |      old EIP       |     " - 20 <---- ESP 
                     +--------------------+             


然后cpu读取IDT的第0个索引（除0对于的vector为0），设置cs：eip指向这个描述符对应的中断处理服务例程；
中断处理服务例程接管控制并处理异常，如结束用户进程；

对于某些类型的异常，除了上面那5个值会被入栈，cpu还会降一个error code入栈。如缺页异常，此时栈如下：


                     +--------------------+ KSTACKTOP             
                     | 0x00000 | old SS   |     " - 4
                     |      old ESP       |     " - 8
                     |     old EFLAGS     |     " - 12
                     | 0x00000 | old CS   |     " - 16
                     |      old EIP       |     " - 20
                     |     error code     |     " - 24 <---- ESP
                     +--------------------+             


####3. 嵌套异常和中断
cpu能处理来自内核和用户态的异常和中断，如果中断发生时，cpu已经处于内核态，此时cpu只需往当前栈push更多变量即可（无需再切换栈），
这样内核就优雅的处理嵌套中断（第二次发送中断时，cpu已在内核态）。此时内核栈多了下面内容：


                     +--------------------+ <---- old ESP
                     |     old EFLAGS     |     " - 4
                     | 0x00000 | old CS   |     " - 8
                     |      old EIP       |     " - 12
                     +--------------------+       

####4.系统调用的实现
根据前文分析，我们首先要做的是建立IDT（包括给每个中断和异常创建对应的服务例程handler，
然后将这些handler设置到对应的IDT中每一项），JOS只要求创建vectors 0-31的中断和异常。

完成上面内容后，然后需要实现系统调用，系统调用是用户态进入内核态的接口，通过指向int指令（软中断）。
用户态进程会将系统调用号和参数放到寄存器中，这样内核不需要查看用户进程的栈，一般系统调用号放入eax中，
参数（最多五个）分别放入：edx, ecx, ebx, edi, esi，然后执行完系统调用后，内核会将返回参数放入eax中
返回给用户进程。


####总结：
用户进程执行涉及到两个部分：
1）内核部分
内核运行sched_yield()，选取一个runnable的进程，然后调用env_run来运行该用户进程。env_run会设置好全局变量curenv（每个cpu一个：curenv = thiscpu->cpu_env，将该变量设为将要运行的进程，并更新新进程状态），然后调用env_pop_tf完成从内核切换到新的用户态进程；

2）用户态部分
用户进程执行入口为lib/entry.S，然后跳转到libmain函数（lib/libmain.c）执行，接着调用umain来执行用户进程的main函数，完后调用exit系统函数。

exit()实现为调用sys_env_destroy()（在lib/syscall.c中，这个用户可调用的系统函数），路线为：

    
    exit  -->  sys_env_destroy --> syscall(syscall_num, ....)；

syscall最重要的参数是系统调用号syscall_num，该函执行int指令来陷入内核，内核中断入口为kern/trapentry.S，那么是如何执行到这个汇编代码来的呢？

在trap_init中设置了每个中断相应的处理服务例程（设置IDT表），以page fault为例，对应中断服务例程为：handler_pgflt，而这些中断服务例程都是定义在trapentry.S中，目前这些handler都会跳到_alltraps中，然后执行trap()函数（trap.c中），trap()会判断trap来自用户态还是内核态，最后执行trap_dispatch，
trap_dispatch根据trap号会去执行相应的函数，如对于T_SYSCALL，则会执行syscall()函数（这个不同于用户态lib/syscall.c的syscall）
