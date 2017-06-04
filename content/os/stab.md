Title: stab释疑
Date: 2014-1-15
Category: os
Tags: os, bootloader, gdb, stab
Author: jin



Reference: https://sourceware.org/gdb/onlinedocs/stabs.html

####1. stabs简介
stabs代表一种信息格式，用来将程序的信息展示给调试器debugger。

####1.2. Debugging information flow
一般编译流程：gcc把.c编译成.s，汇编器把.s转化成.o，链接器把.o和库文件组合生成可执行文件；
当-g选项打开时，gcc会往.s文件中加入额外的调试信息，然后这些调试信息被加入到.o和可执行文件中。
这个调试信息包括c源文件的一些信息，如文件名，行号，变量的类型和范围（type, scope），函数名字，
参数和范围(function names, parameters,scopes)。在最后生成的可执行文件中，会生成一个symbol table
和string table，debugger就是利用这两个表来获取程序的信息的。

注意：

* 当没有-g选项时，我们对可执行文件反汇编命令（objdump -S）时，只能得出汇编指令；

*当有-g选项时，可以得出c代码和对应的汇编指令，行号信息也会加入；

####1.3. stab信息格式
一般有3种stab的汇编指令，即：.stabs(string), .stabn(number), .stabd(dot)，格式分别如下：
     
     * .stabs "string",type,other,desc,value
     
     * .stabn type,other,desc,value
     
     * .stabd type,other,desc

     * .stabx "string",value,type,sdb-type


string格式："name:symbol-descriptor type-information"，其中name是symbol的名字；symbol-descriptor表示symbol的类型，
见（Appendix B Table of Symbol Descriptors）；type-information是一个type-number或者‘type-number=’。

####2. Encoding Structure of program

stabs包含了程序的如下信息：函数名，源文件名和include文件名，行号，函数名字类型以及代码的开始和结束。

