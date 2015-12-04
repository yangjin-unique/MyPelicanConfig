Title: const修饰变了能否被修改
Date: 2015-11-20
Category: c&c++
Tags: C, const, gdb 
Author: jin


今天无意中想到一个问题，const修饰的变量能否被修改，虽然修改const变量是个不好的习惯，
但是仍想去验证一下这个问题。
const一般用于修饰变量或者函数参数，用于函参修饰指针时表示函数不会改变该指针指向
的变量的值，一个经典的问题就是：const int *p 与 int * const p的区别。在c++中，
const还用于修饰成员函数，表示该成员函数不能修改成员变量，只能修改mutable类型的
成员变量。
看下面一段测试代码，g为全局常量，a为局部常量，下面分别通过指针去修改这两个变量的
值，下面程序执行到最后修改g变量时出现segmentation fault，也就是说能修改局部常量，
但不能修改全局定义的常量，因为g是保存在只读数据段.rodata里。
（使用gcc (Ubuntu 4.8.2-19ubuntu1) 4.8.2，运行在 Intel(R) Core(TM) i7-3770 CPU)

    :::c
    const int g = 1;

    int
    main(int argc, char **argv)
    {
        const int a = 2;
        int *pa = (int *) &a;

        printf("a = %d, *pa = %d\n", a, *pa);
        *pa = 3;
        printf("a = %d, *pa = %d\n", a, *pa);
        
        int *pg = (int *) &g;
        printf("g = %d, *pg = %d\n", g, *pg);
        *pg = 4;
        printf("g = %d, *pg = %d\n", g, *pg);
        return;
    }

最后这个问题其实是一个未定义的行为：undefined behavior，与编译器和cpu有关，本实验是
为了小小的验证一下，顺便给debug时一个小小的忠告：不要以为是const就修改不了，还是有
可能被误修改的！！！
