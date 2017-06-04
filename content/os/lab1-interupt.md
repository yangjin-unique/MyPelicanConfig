Title: x86中断与异常
Date: 2014-1-15
Category: os
Tags: os, x86, interrupt, trap
Author: jin


####1、三种特殊的中断事件
异步中断(asynchronous	interrupt)也称外部中断,简称中断 (interrupt)：由CPU外部设备引起的外部事件如I/O中断、
时钟中断、控制台中断等是异步产生的 （即产生的时刻不确定），与CPU的执行无关;

异常(exception)：而把在CPU执行指令期间检测到不正常的或非法的条件(如除零错、地访问越界)所引起的内部事件称作
同步中断(synchronous	interrupt);

异常：把在程序中使用请求系统服务的系统调用而引发的事件， 称作陷入中断(trap	interrupt)，也称软中断(soft	interrupt)，
系统调用(system	call)简称trap。

####2、保护模式下的中断处理过程

当CPU收到中断（通过8259A完成，有关8259A的信息请看附录A）或者异常的事件时，它会暂停执行当前的程序或任务，
通过一定的机制跳转到负责处理这个信号的相关处理例程中，在完成对这个事件的处 理后再跳回到刚才被打断的程序或任务中。

中断向量和中断服务例程的对应关系主要是由IDT（中断描述符表）负责。操作 系统在IDT中设置好各种中断向量对应的中断描述符，
留待CPU在产生中断后查询对应中断服务例程的起始地址。而IDT本身 的起始地址保存在idtr寄存器中。

1）中断描述符表IDT
中断描述符表把每个中断或异常编号和一个指向中断服务例程的描述符联系起来。同GDT一样，IDT是一个8字节的描述符数组，
但IDT的第一项可以包含一个描述符。CPU把中断（异常）号乘以8做为 IDT的索引。IDT可以位于内存的任意位置，
CPU通过IDT寄存器（IDTR）的内容来寻址IDT的起始地址。指令LIDT和SIDT用来操作IDTR。

两条指令都有一个显示的操作数：一个6字节表示的内存地址。指令的含义如下： 

* LIDT（Load	IDT	Register）指令：使用一个包含线性地址基址和界限的内存操作数来加载IDT。操作系统创建IDT时需要
执行它来设定IDT的起始地址。这条指令只能在特权级0执行。（可参见libs/x86.h中的lidt函数实现，其实就是一条汇编指令）

* SIDT（Store	IDT	Register）指令：拷贝IDTR的基址和界限部分到一个内存地址。这条指令可以在任意特权级执行。

在保护模式下，最多会存在256个Interrupt/Exception	Vectors。范围[0，31]内的32个向量被异常Exception和NMI使用，但当
前并非所有这32个向量都已经被使用，有几个当前没有被使用的，请不要擅自使用它们，它们被保留，以备将来可能增加新 的Ex
ception。范围[32，255]内的向量被保留给用户定义的Interrupts。


2）IDT门描述符
Interrupts/Exceptions应该使用Interrupt	Gate和Trap	Gate，它们之间的唯一区别就是：当调用Interrupt	Gate时，Interrupt会
被CPU自动禁止；而调用Trap	Gate时，CPU则不会去禁止或打开中断，而是保留它原来的样子。

所谓“自动禁止”，指的是CPU跳转到interrupt	gate里的地址时，在将EFLAGS保存到栈上之后，清除EFLAGS
里的IF位，以避免重复触发中断。在中断处理例程里，操作系统可以将EFLAGS里的IF设上,从而允许嵌套中断。但是
必须在此之前做好处理嵌套中断的必要准备，如保存必要的寄存器等。二在ucore中访问Trap	Gate的目的是为了实现
系统调用。用户进程在正常执行中是不能禁止中断的，而当它发出系统调用后，将通过Trap	Gate完成了从用户态 
（ring	3）的用户进程进了核心态（ring	0）的OS	kernel。如果在到达OS	kernel后禁止EFLAGS里的IF位，
第一没意义 （因为不会出现嵌套系统调用的情况），第二还会导致某些中断得不到及时响应，所以调用Trap	Gate时，
CPU则不会 去禁止中断。总之，interrupt	gate和trap	gate之间没有优先级之分，仅仅是CPU在处理中断时有不同的方法，
供操作 系统在实现时根据需要进行选择。

IDT包含3中类型的描述符：

* Task-gate	descriptor	（这里没有使用）

* Interrupt-gate	descriptor	（中断方式用到）

* Trap-gate	descriptor（系统调用用到）
