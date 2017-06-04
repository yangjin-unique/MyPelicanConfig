Title: Makefile函数 
Date: 2016-1-17
Category: linux
Tags: Makefile
Author: jin

利用Makefile自带的函数能更一部精简我们的Makefile的编写，下面介绍一下常用的几个函数。
####1. 通配符函数wildcard
Makefile中通配符扩展是在规则中自动进行的，但是如果要对一个变量进行类似的操作时，我们就需要使用这个wildcard
这个函数来进行扩展，用法如下：
    $(wildcard pattern...)
这个函数会将符合这个pattern模式的所有文件以空格为分隔符列出来，例如我们要获取src目录下所有的.c文件，则实现为：
    SRC = $(wildcard *.c)
假设src目录下有a.c和b.c两个文件，那么SRC相当于如下：
    SRC = a.c b.c

####2. 字符串操作函数
常用的有notdir, subst, patsubst, strip, filter, findstring等。

1) $(notdir text)
notdir用于去掉字符串中路径名，如：

    NO_DIR = $(notdir src/a.c)

也就等同于：

    NO_DIR = a.c

2) $(patsubst pattern, replacement, text)
patsubst用于将字符串text中符合pattern的字串替换为replacement字串，如：

    OBJS = $(patsubst %.c,%.o, a.c b.c)

则相当于：

    OBJS = a.o b.o

3) $(subst from, to, text)
subst用于将text中from字串替换为to字串，如：

    OBJS = $(subst ee,EE, feet on the street)

也就相当于：

    OBJS = fEEt on the strEEt

下面来通过一个例子来说明如何利用上面的函数来精简我们的Makefile。假设我们有个项目prj，c源代码都放在src目录中，
头文件都放在include目录下，我们想让生成的目标文件都在objs目录下，文件组织如下：
    
    +++prj/
    +++++++src/
    +++++++include/
    +++++++objs/
    +++Makefile

此时我们可在Makefile中加上如下：
    
    SRC = $(wildcard prj/*.c)
    NO_DIR_SRC = $(notdir $(SRC))
    OBJS = $(patsubst %.c, objs/%.o, $(NO_DIR_SRC))

这要我们就很方便的得到了SRC和OBJS。

####References:
https://www.gnu.org/software/make/manual/
