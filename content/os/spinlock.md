Title: spinlock的实现
Date: 2014-6-1
Category: os
Tags: Multi-processor, spinlock
Author: jin


spinlock在多核多线程的场景中使用非常广泛，采用busy_wait_loop忙等待的方式，与信号量相比的优点在于不会进程上下文的切换（进程的调度），节省了进程切换带来的敖贵的系统开销。一般用spinlock时，要保证临界区的代码短小，等待的时间较短。linux内核中很多地方都使用了spinlock，如中断上下文中使用（多核），用户态多进程pthread提供了spinlock的API。spinlock的实现一般采用cpu提供的原子指令（atomic）来实现，如Test-and-Set，Compare-and-Swap。
JOS内核提供了spinlock，采用CAS（使用x86的xchg指令）方法实现。
spinlock的定义如下：

    :::c
    // Mutual exclusion lock.
    struct spinlock {
        unsigned locked;       // Is the lock held?

    #ifdef DEBUG_SPINLOCK
        // For debugging:
        char *name;            // Name of lock.
        struct CpuInfo *cpu;   // The CPU holding the lock.
        uintptr_t pcs[10];     // The call stack (an array of program counters)
                               // that locked the lock.
    #endif
    };

lock与unlock如下：

    :::c
    void
    __spin_initlock(struct spinlock *lk, char *name)
    {
        lk->locked = 0;
    #ifdef DEBUG_SPINLOCK
        lk->name = name;
        lk->cpu = 0;
    #endif
    }

    // Acquire the lock.
    // Loops (spins) until the lock is acquired.
    // Holding a lock for a long time may cause
    // other CPUs to waste time spinning to acquire it.
    void
    spin_lock(struct spinlock *lk)
    {
    #ifdef DEBUG_SPINLOCK
        if (holding(lk))
            panic("CPU %d cannot acquire %s: already holding", cpunum(), lk->name);
    #endif

        // The xchg is atomic.
        // It also serializes, so that reads after acquire are not
        // reordered before it. 
        while (xchg(&lk->locked, 1) != 0)
            asm volatile ("pause");

        // Record info about lock acquisition for debugging.
    #ifdef DEBUG_SPINLOCK
        lk->cpu = thiscpu;
        get_caller_pcs(lk->pcs);
    #endif
    }

    // Release the lock.
    void
    spin_unlock(struct spinlock *lk)
    {
    #ifdef DEBUG_SPINLOCK
        if (!holding(lk)) {
            int i;
            uint32_t pcs[10];
            // Nab the acquiring EIP chain before it gets released
            memmove(pcs, lk->pcs, sizeof pcs);
            cprintf("CPU %d cannot release %s: held by CPU %d\nAcquired at:", 
                cpunum(), lk->name, lk->cpu->cpu_id);
            for (i = 0; i < 10 && pcs[i]; i++) {
                struct Eipdebuginfo info;
                if (debuginfo_eip(pcs[i], &info) >= 0)
                    cprintf("  %08x %s:%d: %.*s+%x\n", pcs[i],
                        info.eip_file, info.eip_line,
                        info.eip_fn_namelen, info.eip_fn_name,
                        pcs[i] - info.eip_fn_addr);
                else
                    cprintf("  %08x\n", pcs[i]);
            }
            panic("spin_unlock");
        }

        lk->pcs[0] = 0;
        lk->cpu = 0;
    #endif

        // The xchg serializes, so that reads before release are 
        // not reordered after it.  The 1996 PentiumPro manual (Volume 3,
        // 7.2) says reads can be carried out speculatively and in
        // any order, which implies we need to serialize here.
        // But the 2007 Intel 64 Architecture Memory Ordering White
        // Paper says that Intel 64 and IA-32 will not move a load
        // after a store. So lock->locked = 0 would work here.
        // The xchg being asm volatile ensures gcc emits it after
        // the above assignments (and after the critical section).
        xchg(&lk->locked, 0);
    }
