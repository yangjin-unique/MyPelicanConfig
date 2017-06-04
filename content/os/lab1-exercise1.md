Title: lab1 exercise1
Date: 2014-1-16
Category: os
Tags: os, bootloader
Author: jin


lab1主要熟悉qemu x86使用环境，各种实验工具，包括qemu与gdb联合调试等，熟悉pc的bootstrap过程，包括BIOS和bootloader。
该练习主要是实现一个backtrace函数，解析当前函数调用栈帧，并需要解析出当前函数的文件名、函数名、行号信息，如下面所示：

    K> backtrace
    Stack backtrace:
      ebp f010ff78  eip f01008ae  args 00000001 f010ff8c 00000000 f0110580 00000000
             kern/monitor.c:143: monitor+106
      ebp f010ffd8  eip f0100193  args 00000000 00001aac 00000660 00000000 00000000
             kern/init.c:49: i386_init+59
      ebp f010fff8  eip f010003d  args 00000000 00000000 0000ffff 10cf9a00 0000ffff
             kern/entry.S:70: <unknown>+0
    K>

1. 解析函数调用栈帧需要理解x86函数调用时寄存器ebp、esp、eip的操作，以及函数参数、返回地址等如何入栈。
ebp来记录栈帧的开始，同时ebp指向的地址的内容是上一个函数栈帧的ebp。这样由ebp就形成了一个单链表，
将所有的函数调用栈帧连在一起。栈一般是由高地址向低地址生长。
一般来说，对于大多数编译器，函数入口的汇编代码一般如下：


    push %ebp
    mov %esp,%ebp
    sub $X, %esp

但是在我的机器上生成的汇编代码却不是这样，这个与编译器FPO：frame-pointer-omission有关，编译器会决定是否需要ebp，一般简单的函数不需要ebp，而复杂的函数需要）。


2. 解析文件名、函数名、行号信息，这个实际上gdb干的工作，我们在编译代码是加上-g选项，
编译器会加入额外的信息到可执行文件，gdb就是靠这些信息来工作的。当-g选项打开时，
gcc会往.s文件中加入额外的调试信息，然后这些调试信息被加入到.o和可执行文件中。
这个调试信息包括c源文件的一些信息，如文件名，行号，变量的类型和范围（type, scope），
函数名字，参数和范围(function names, parameters,scopes)。在最后生成的可执行文件中，
会生成一个symbol table和string table，debugger就是利用这两个表来获取程序的信息的。
所以我们的代码 也是利用这个来解析即可，最后贴上整个练习的源代码：


    :::c
    int
    mon_backtrace(int argc, char **argv, struct Trapframe *tf)
    {
        // Your code here.
        uint32_t ebp = read_ebp();
        uint32_t eip;
        struct Eipdebuginfo info;
        int offset = 0;

        while (ebp != 0) {
            cprintf("ebp %08x eip %08x args %08x %08x %08x %08x %08x\n", 
                    ebp, (uint32_t)*((uint32_t *)(ebp+4)), 
                     (uint32_t)*((uint32_t *)(ebp+8)), 
                     (uint32_t)*((uint32_t *)(ebp+12)), 
                     (uint32_t)*((uint32_t *)(ebp+16)), 
                     (uint32_t)*((uint32_t *)(ebp+20)), 
                     (uint32_t)*((uint32_t *)(ebp+24)), 
                     (uint32_t)*((uint32_t *)(ebp+4)) 
                    );
            eip = (uint32_t) *((uint32_t *)(ebp+4));
            debuginfo_eip(eip, &info);
            offset = info.eip_fn_addr - eip; 
            cprintf("%s:%d: %.*s+%d\n", info.eip_file, info.eip_line,
                        info.eip_fn_namelen, info.eip_fn_name, offset);
            ebp = (uint32_t) *((uint32_t *)ebp);
        }
        return 0;
    }


