Title: lab3:user mode切换到kernel mode所涉及的数据结构
Date: 2013-3-1
Category: os
Tags: os, user mode, kernel mode, tast state, TrapFrame
Author: jin


其实这两个没有太大关系，Taskstate前面已提到，这个在cpu初始化时会调用trap_init_percpu将设置这个结构体中的栈寄存器和段寄存器：
tss->ts_esp0 = 每个cpu的栈top;
tss->ts_ss0 = GD_KD; 内核的数据段选择子

每个cpu都有一个这样的结构：thiscpu->cpu_ts，这个是为了当从用户态切换到内核态时，让cpu能找到内核栈和数据段的地址。
发生这种切换时，内核也必须保存当前用户进程的状态，以便返回时可以继续执行，用户进程的状态就保存在TrapFrame结构中，
那么cpu是怎么做的呢？
先看TrapFrame结构：

    :::c
    struct PushRegs {
        /* registers as pushed by pusha */
        uint32_t reg_edi;
        uint32_t reg_esi;
        uint32_t reg_ebp;
        uint32_t reg_oesp;        /* Useless */
        uint32_t reg_ebx;
        uint32_t reg_edx;
        uint32_t reg_ecx;
        uint32_t reg_eax;
    } __attribute__((packed));

    struct Trapframe {
        struct PushRegs tf_regs;
        uint16_t tf_es;
        uint16_t tf_padding1;
        uint16_t tf_ds;
        uint16_t tf_padding2;
        uint32_t tf_trapno;
        /* below here defined by x86 hardware */
        uint32_t tf_err;
        uintptr_t tf_eip;
        uint16_t tf_cs;
        uint16_t tf_padding3;
        uint32_t tf_eflags;
        /* below here only when crossing rings, such as from user to kernel */
        uintptr_t tf_esp;
        uint16_t tf_ss;
        uint16_t tf_padding4;
    } __attribute__((packed));


上面这些值（主要是寄存器）就是cpu从用户态切换到内核态需要保存的（PushRegs里面的通用寄存器是用于向内核传递参数，如系统调用号就是用eax传递的，返回值也是eax；然后是段寄存器，cs：eip用于返回时继续执行）。切换的入口在trapentry.S中：
以系统调用的代码为例：
这个handler_sysall的代码：

    #define TRAPHANDLER_NOEC(name, num)                    \
        .globl name;                            \
        .type name, @function;                        \
        .align 2;                            \
        name:                                \
        pushl $0;                            \
        pushl $(num);                            \
        jmp _alltraps
    
下面是_alltraps的代码：


    .globl _alltraps
    .type _alltraps, @function
    .align 2
    _alltraps:
        pushl %ds
        pushl %es
        pushal

        movw $GD_KD, %ax
        movw %ax, %ds
        movw %ax, %es

        pushl %esp
        call trap
        addl $4, %esp
    .globl trapret
    trapret:
        popal
        pop %es
        pop %ds
        addl $0x8, %esp
        iret

_alltraps中会调用trap()函数，我们知道trap函数的参数TrapFrame，所以这个TrapFrame参数是在前面两段汇编代码里面传进去的，现在好办了，只要看看这些汇编代码是怎么处理栈（参数是通过栈传递）？
由于栈是从高地址往低地址生长，所以入栈的顺序应该与寄存器在TrapFrame的位置顺序相反：
也就是从call trap指令往上看，先pushal，这个对应将PushRegs入栈，然后es，ds，再到num，0为止。tf_trapno后面的值都不是这里操作的。

