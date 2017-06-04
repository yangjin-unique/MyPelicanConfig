Title: entry.S
Date: 2014-1-16
Category: os
Tags: os, bootloader, entry.S
Author: jin





lab1提到bootloader的c文件最后会加载内核到物理地址0x10000处（64K）处，然后再执行内核的入口entry.S函数。

这里要特别注意：在此之前，所有的都是直接操作物理地址（怎么做到的？实时模式就不用说了，16位寻址1MB，
进入保护模式后，32位，bootloader把所有段寄存器设成0，除了esp，这个必须设置到正确的物理地址。
而且分页机制也没有使能，所以线性地址就是物理地址）。

在编译image时，kernel.ld会将内核的c代码的（entry.S仍在物理地址空间执行）起始地址链接到0xF0100000，也就是当内核执行c代码main时，
所有的指令的寻址都是以这个为基础，但是内核的实际物理地址是在0x100000，所以进入内核后第一件事就是要建立一个映射：
将起始地址为0xF0100000映射到物理地址0x100000（为以后的c代码执行准备好）。

内核入口函数entry.S中（仍在物理地址空间0x100000执行），一开始就是做这件事，使能分页机制（设置CR0）：


     # Load the physical address of entry_pgdir into cr3.  entry_pgdir
     # is defined in entrypgdir.c.
     movl	$(RELOC(entry_pgdir)), %eax      #entry_pgdir是定义在内核的c代码中，所以其地址是以0xF0100000为基础，
                                             #所以RELOC(entry_pgdir)是把它转化为对应的物理地址
     movl	%eax, %cr3
     movl	%cr0, %eax # Turn on paging.
     orl	$(CR0_PE|CR0_PG|CR0_WP), %eax
     movl	%eax, %cr0
     # Now paging is enabled, but we're still running at a low EIP
     # (why is this okay?).  Jump up above KERNBASE before entering
     # C code.
     mov	$relocated, %eax
     jmp	*%eax
    relocated:
     # Clear the frame pointer register (EBP)
     # so that once we get into debugging C code,
     # stack backtraces will be terminated properly.
     movl	$0x0,%ebp	 # nuke frame pointer，这个用于lab1解析栈帧用作循环结尾的条件
     # Set the stack pointer
     movl	$(bootstacktop),%esp
     # now to C code
     call	i386_init
     # Should never get here, but in case we do, just spin.
    spin:	jmp	spin

此后，内核进入main的c代码，在虚拟地址空间执行。
