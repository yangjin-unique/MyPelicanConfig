Title: 利用Debugfs调试linux kernel
Date: 2015-12-28
Category: os
Tags: linux, kernel, debugfs
Author: jin

调试内核的方法很多，debugfs就是其中一种利用虚拟文件系统来调试内核的方法之一，debugfs与profs，sysfs类似，
是一种虚拟文件系统。默认情况下，debugfs文件系统挂载在/sys/kernel/debug/目录下，也可用手动命令来加载：
    mount -t debugfs none /<your dir>/debugfs

下面的示例将建立一个内核模块debugfs_hello，并在该内核模块中调用debugfs的API创建下面3个值：
/sys/kernel/debug/debugfs_hello/hello
/sys/kernel/debug/debugfs_hello/add
/sys/kernel/debug/debugfs_hello/sum
其中hello是一个可读写的整数值，即用户可用cat和echo命令来查看和修改该；
add是可写的，当用户调用echo命令向其写入一个值，该值会被内核模块加到sum这个值中；
sum是只读的，用于计算所有输入给add的值的总和，用户可用cat命令查看该值。

    :::c
    #include <linux/module.h>
    #include <linux/kernel.h>
    #include <linux/debugfs.h>

    static struct dentry *dir = NULL;

    static unsigned int debugfs_hello;

    static u32 sum = 0;

    static int add_write(void *data, u64 value)
    {
        sum += value;
        return 0;
    }

    DEFINE_SIMPLE_ATTRIBUTE(add_ops, NULL, add_write, "%llu\n");

    static __init int hello_init(void)
    {
        struct dentry *tmp_dir = NULL;

        /* create /sys/kernel/debug/debugfs_hello/ directory */
        dir = debugfs_create_dir("debugfs_hello", NULL);
        if (!dir) {
            printk(KERN_ALERT "debugfs_create_dir failed\n");
            return -1;
        }

        /* create /sys/kernel/debug/debugfs_hello/hello value, mode: rw*/
        tmp_dir = debugfs_create_u32("hello", 00666, dir, &debugfs_hello);
        if (!tmp_dir) {
            printk(KERN_ALERT "debugfs_create_u32 failed\n");
            return -1;
        }

        /* create /sys/kernel/debug/debugfs_hello/add value, mode: w*/
        tmp_dir = debugfs_create_file("add", 0222, dir, NULL, &add_ops);
        if (!tmp_dir) {
            printk(KERN_ALERT "debugfs_create_file failed\n");
            return -1;
        }

        /* create /sys/kernel/debug/debugfs_hello/sum value, mode: r*/
        tmp_dir = debugfs_create_u32("sum", 0444, dir, &sum);
        if (!tmp_dir) {
            printk(KERN_ALERT "debugfs_create_u32 failed\n");
            return -1;
        }

        return 0;
    }


    static void __exit hello_exit(void)
    {
        printk(KERN_INFO "Exit debugfs_hello module\n");
        debugfs_remove_recursive(dir);
        dir = NULL;
    }

    module_init(hello_init);
    module_exit(hello_exit);

    MODULE_LICENSE("Dual BSD/GPL");
    MODULE_DESCRIPTION("Debugfs hello examle");

Makefile如下，其中第一条是为了避免编译驱动时出现kernel module verification failed: signature and/or required key missing错误：
    
    :::c
    CONFIG_MODULE_SIG=n

    obj-m = debugfs_hello.o
    KVERSION = $(shell uname -r)
    PWD = $(shell pwd)
    all:
            make -C /lib/modules/$(KVERSION)/build M=$(PWD) modules
    clean:
            make -C /lib/modules/$(KVERSION)/build M=$(PWD) clean
