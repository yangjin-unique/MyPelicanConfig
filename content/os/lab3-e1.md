Title: lab3:加载用户进程
Date: 2014-3-1
Category: os
Tags: os, bootloader, gdb, stab
Author: jin


该练习主要完成内核加载用户进程，包括用户进程环境的初始化，创建用户进程，加载用户进程等。
主要完成以下几个函数的实现：
* env_init()：初始化用户进程，配置每个段的优先级特权级；

* env_setup_vm()：给每个进程分配一个页目录，并初始化用户地址空间的内核部分；

* region_alloc()：给用户进程分配物理内存并将物理地址映射到进程的虚拟地址空间；

* load_icode()：解析用户进程elf文件，并加载到用户地址空间；

* env_create()：调用env_alloc和load_icode；

* env_run()：在用户模式下执行进程；

由于此时还没有文件系统，此时是将用户的进程elf文件嵌入到内核的image中，最后生成的
kernel.sym包含一些特殊的符号，这个符号实际上就是用户程序的elf文件，最后由内核加载
并执行。

每个用户进程都有一个相应的结构体：

    :::c

    struct Env {
        struct Trapframe env_tf;	// Saved registers
        struct Env *env_link;		// Next free Env
        envid_t env_id;			// Unique environment identifier
        envid_t env_parent_id;		// env_id of this env's parent
        enum EnvType env_type;		// Indicates special system environments
        unsigned env_status;		// Status of the environment
        uint32_t env_runs;		// Number of times environment has run

        // Address space
        pde_t *env_pgdir;		// Kernel virtual address of page dir
    };


该练习的难点在于load_icode的实现（其它的实现就不解释了），该函数先解析用户的elf文件，解析时需要熟悉
elf文件的结构（前面文章已分析）。将每个段（.text, .data）解析后，同时需要拷贝用户进程的地址
空间。由于这个拷贝过程用到的虚拟地址是属于用户进程空间，所以这里要切换到用户进程的页目录，
待解析完后，再切换回内核的页目录。

    :::c
    static void
    load_icode(struct Env *e, uint8_t *binary)
    {
        
        // LAB 3: Your code here.
        struct Elf *elfh = (struct Elf *) binary;

        if (elfh->e_magic != ELF_MAGIC)
            goto bad;

        struct Proghdr *ph = (struct Proghdr *) (binary + elfh->e_phoff);
        struct Proghdr *eph = ph + elfh->e_phnum;

        lcr3(PADDR(e->env_pgdir));
        for (; ph < eph; ph++) {
            if (ph->p_type != ELF_PROG_LOAD) 
                continue;
            region_alloc(e, (void *)ph->p_va, ph->p_memsz);
            memset((void *)ph->p_va, 0, ph->p_memsz);
            memcpy((void *)ph->p_va, (void *)(binary + ph->p_offset), ph->p_filesz);
        }
        lcr3(PADDR(kern_pgdir));
        e->env_tf.tf_eip = elfh->e_entry; //set eip to elf->entry

        // Now map one page for the program's initial stack
        // at virtual address USTACKTOP - PGSIZE.

        // LAB 3: Your code here.
        region_alloc(e, (void *)(USTACKTOP - PGSIZE), PGSIZE);
        return;
    bad:
        panic("load_icode: bad elf image\n");
    }



