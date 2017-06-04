Title: 多进程IPC机制实现
Date: 2014-6-16
Category: os
Tags: Multi-processor, multi-process, IPC
Author: jin



这是lab4最后一个任务，实现进程间的通信IPC，主要完成kern/syscall.c里面的两个API：
sys_ipc_recv和sys_ipc_try_send，以及lib/syscall.c的提供给用户的系统调用：ipc_recv和ipc_send。实现代码如下：

    :::c
    static int
    sys_ipc_try_send(envid_t envid, uint32_t value, void *srcva, unsigned perm)
    {
        // LAB 4: Your code here.
        struct Env *env = NULL;
        struct PageInfo *page = NULL;
        int r;

        if ((r = envid2env(envid, &env, 0)) < 0) {
            return r;
        }
        /* make sure that dst is waiting for us */
        if (env->env_ipc_recving != 1) {
            return -E_IPC_NOT_RECV;
        }

        if (((uintptr_t)srcva > UTOP) || ((uintptr_t)srcva % PGSIZE) != 0)
            return -E_INVAL;

        if ((uintptr_t)srcva < UTOP &&  (perm & PTE_U) != PTE_U) {
            cprintf("perm not valid\n");
            return -E_INVAL;
        }
        if (env->env_ipc_dstva != (void *) UTOP && srcva != (void *)UTOP) {
            if ((perm & PTE_W) == PTE_W) {
                pte_t *pte = NULL;
                if ((page = page_lookup(curenv->env_pgdir, srcva, &pte)) == NULL)
                    return -E_INVAL;
                if ((*pte & PTE_W) != PTE_W)
                    return -E_INVAL;
            }
            /* insert page into dst env's pgdir */ 
            if (page_insert(env->env_pgdir, page, env->env_ipc_dstva, perm) < 0) {
                return -E_NO_MEM;
            }
            env->env_ipc_perm = perm;
        }
        else {
            env->env_ipc_perm = 0;
        }

        /* now set dst env safely... */
        env->env_ipc_recving = 0;
        env->env_ipc_from = curenv->env_id;
        env->env_ipc_value = value;
        if (page != NULL)
            env->env_ipc_perm = perm;
        else
            env->env_ipc_perm = 0;

        env->env_tf.tf_regs.reg_eax = 0;
        /* set des env not block, RUNNABLE now ... */
        //cprintf("sys_ipc_try_send: %x send to %x, set recver runnalbe\n", curenv->env_id, env->env_id);
        env->env_status = ENV_RUNNABLE;
        return 0;
    }

    int32_t
    ipc_recv(envid_t *from_env_store, void *pg, int *perm_store)
    {
        // LAB 4: Your code here.
        int r;

        if (!pg) pg = (void *)UTOP;
        if ((r = sys_ipc_recv(pg)) < 0) {
            if (from_env_store) 
                *from_env_store = 0;
            if (perm_store) 
                *perm_store = 0;
            return r;
        }
        //cprintf("ipc_recv: env=%x receive finish\n", thisenv->env_id);
        if (from_env_store) 
            *from_env_store = thisenv->env_ipc_from;
        if (perm_store) 
            *perm_store = thisenv->env_ipc_perm;
        return thisenv->env_ipc_value;
    }

    void
    ipc_send(envid_t to_env, uint32_t val, void *pg, int perm)
    {
        // LAB 4: Your code here.
        int r;

        if (!pg) pg = (void *)UTOP;

        while ((r = sys_ipc_try_send(to_env, val, pg, perm)) < 0) {
            if (r != -E_IPC_NOT_RECV)
                panic("ipc_send panic\n");
            sys_yield();
        }
    }

