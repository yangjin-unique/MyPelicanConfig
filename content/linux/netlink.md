Title: 如何在linux内核模块中加入netlink通信接口
Date: 2015-12-18
Category: linux
Tags: linux kernel, netlink
Author: jin

与系统调用，/proc，sysfs等类似，netlink也是一种用于用户进程与内核通信的机制，它是基于BSD套接字协议，
使用AF_NETLINK地址簇。
与系统调用，proc，sysfs文件系统等方式相比，netlink具有简单，支持双向通信的特点，并支持消息多播机制。
当我们编写内核驱动并需要与用户进程通信时，我们便能利用netlink来实现这个通信机制。hostapd（一个无线
AP的dameon）中就是采用netlink接口（nl80211）与内核进行通信，下文将通过一个实例来说明如何在自己的内核
模块中支持netlink通信。

####1. 编写内核模块
首先编写内核模块文件：netlink_hello_mod.c，并增加相应的makefile，代码如下：

netlink_hello_mod.c:

    :::c
    #include <linux/module.h>
    #include <net/sock.h>
    #include <linux/netlink.h>
    #include <linux/skbuff.h>

    #define MY_NETLINK_TYPE 31 //max is 32, see netlink.h

    struct sock *my_nl_sock = NULL;

    static void hello_nl_recv_msg(struct sk_buff *skb)
    {
        struct nlmsghdr *nlh;
        int pid;
        struct sk_buff *skb_out;
        int msg_size;
        char *msg = "Hello from kernel";
        int res;

        printk(KERN_INFO "Entering: %s\n", __FUNCTION__);
        msg_size = strlen(msg);
        nlh = (struct nlmsghdr *)skb->data;
        printk(KERN_INFO "Netlink receive msg: %s\n", (char *)nlmsg_data(nlh));

        pid = nlh->nlmsg_pid;
        skb_out = nlmsg_new(msg_size, 0);
        if (!skb_out) {
            printk(KERN_INFO "alloc nlmsg failed\n");
            return;
        }
        nlh = nlmsg_put(skb_out, 0, 0, NLMSG_DONE, msg_size, 0);
        NETLINK_CB(skb_out).dst_group = 0;
        strncpy(nlmsg_data(nlh), msg, msg_size);

        res = nlmsg_unicast(my_nl_sock, skb_out, pid);
        if (res < 0)
            printk(KERN_INFO "nlmsg unicast failed\n");
        return;
    }

    static int __init hello_init(void)
    {
        struct netlink_kernel_cfg cfg = {
                .groups = 0,
                .input = hello_nl_recv_msg
        };
        
        printk("Entering: %s:\n", __FUNCTION__);
        my_nl_sock = netlink_kernel_create(&init_net, MY_NETLINK_TYPE, &cfg);

        if (!my_nl_sock) {
            printk(KERN_ALERT "netlink create sock failed\n");
            return -10;
        }
        return 0;
    }

    static void __exit hello_exit(void)
    {
        printk(KERN_INFO "Exiting hello module\n");
        netlink_kernel_release(my_nl_sock);
        my_nl_sock = NULL;
    }

    module_init(hello_init);
    module_exit(hello_exit);

    MODULE_LICENSE("Dual BSD/GPL");
    MODULE_AUTHOR("Yangjin");
    MODULE_DESCRIPTION("netlink hello module");

Makefile:

    :::C
    obj-m = netlink_hello_mod.o
    KVERSION = $(shell uname -r)
    PWD = $(shell pwd)
    all:
            make -C /lib/modules/$(KVERSION)/build M=$(PWD) modules
    clean:
            make -C /lib/modules/$(KVERSION)/build M=$(PWD) clean

####2. 编写用户进程代码
用户进程主要使用netlink的socket与内核进行通信，首先向内核发送一条消息，然后再接收内核的
消息，代码如下:

    :::c
    #include <stdlib.h>
    #include <stdio.h>
    #include <string.h>
    #include <sys/socket.h>
    #include <linux/netlink.h>

    #define MY_NETLINK_TYPE 31
    #define MAX_PAYLOAD 1024 /* maximum payload size*/

    struct sockaddr_nl src_addr, dest_addr;
    struct nlmsghdr *nlh = NULL;
    struct iovec iov;
    int sock_fd;
    struct msghdr msg;

    int 
    main(int argc, char *argv[])
    {
        sock_fd = socket(PF_NETLINK, SOCK_DGRAM, MY_NETLINK_TYPE);
        if (sock_fd < 0)
            return -1;

        memset(&src_addr, 0, sizeof(src_addr));
        src_addr.nl_family = AF_NETLINK;
        src_addr.nl_pid = getpid(); /* self pid */

        bind(sock_fd, (struct sockaddr *)&src_addr, sizeof(src_addr));

        memset(&dest_addr, 0, sizeof(dest_addr));
        memset(&dest_addr, 0, sizeof(dest_addr));
        dest_addr.nl_family = AF_NETLINK;
        dest_addr.nl_pid = 0; /* For Linux Kernel */
        dest_addr.nl_groups = 0; /* unicast */

        nlh = (struct nlmsghdr *)malloc(NLMSG_SPACE(MAX_PAYLOAD));
        memset(nlh, 0, NLMSG_SPACE(MAX_PAYLOAD));
        nlh->nlmsg_len = NLMSG_SPACE(MAX_PAYLOAD);
        nlh->nlmsg_pid = getpid();
        nlh->nlmsg_flags = 0;

        strcpy(NLMSG_DATA(nlh), "Hello");

        iov.iov_base = (void *)nlh;
        iov.iov_len = nlh->nlmsg_len;
        msg.msg_name = (void *)&dest_addr;
        msg.msg_namelen = sizeof(dest_addr);
        msg.msg_iov = &iov;
        msg.msg_iovlen = 1;

        printf("Sending message to kernel\n");
        sendmsg(sock_fd, &msg, 0);
        printf("Waiting for message from kernel\n");

        /* Read message from kernel */
        recvmsg(sock_fd, &msg, 0);
        printf("Received message payload: %s\n", NLMSG_DATA(nlh));
        close(sock_fd);
        return 0;
    }

####3. 测试结果
先make一下编译生成我们的内核模块文件：netlink_helloc_mod.ko，然后加载该模块：
#: insmod netlink_hello_mod.ko
加载后可用lsmod查看是否加载成功，然后编译并运行用户进程hello_user，可在终端
中看到如下结果：

    Sending message to kernel
    Waiting for message from kernel
    Received message payload: Hello from kernel

上面是用户进程的输出，可用dmesg命令查看内核模块的输出（或者直接查看/var/log/kern）.
