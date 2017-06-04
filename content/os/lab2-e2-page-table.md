Title: lab2-exercise2：页表
Date: 2014-2-1
Category: os
Tags: os, page table, page directory, address translation
Author: jin



lab2的exercise1主要完成物理页的管理，建立一个简单的内存管理机制，后面的练习需要用到内存分配都是这里完成的，小结一下exercise1的要点：
完成物理内存的管理机制：主要是建立pages[]与物理页的一一映射（包括设置可用和不可用的物理页，pages数组的index就是物理内存地址pa的高22位）；
exercise2主要内容是完成y页目录和页表的建立，从而建立起虚拟地址空间与物理地址空间的映射，主要是实现以下几个函数：


* pgdir_walk()
* boot_map_region()
* page_lookup()
* page_remove()
* page_insert()

####1. pgdir_walk
给定一个页目录，该函数返回一个虚拟地址对应的在页目录中的页表项page table entry（PTE）的地址。
当该虚拟地址对应的页表不存在时，会创建一个页表。后面几个函数的实现都会依赖该函数.


    :::c
    pte_t *
    pgdir_walk(pde_t *pgdir, const void *va, int create)
    {
        // Fill this function in
        pde_t pde;
        pte_t *pte;
        struct PageInfo *page;

        pde  = pgdir[PDX(va)];
        if (pde & PTE_P) {
            pte = KADDR(PTE_ADDR(pde));
            return &pte[PTX(va)];
        }

        if (create == false) {
            return NULL;
        }
        /* crete a new page table with a new page  */
        page = page_alloc(ALLOC_ZERO);
        if (!page)
            return NULL;
        pde = page2pa(page);
        pgdir[PDX(va)] = pde| PTE_P | PTE_W | PTE_U;//将新分配的页表加入到页目录中
        page->pp_ref++;

        return &((pte_t*) page2kva(page))[PTX(va)];//返回该页表中的va对应的页表项的地址
    }

####2. page_lookup
查找映射在虚拟地址va对应的物理page，方法就是先利用pgdir_walk找到该va对应的页表项，如果页表
存在则表示有相应的物理页，并返回该物理页对应的pages[]，否则，表示还该虚拟地址还没有被映射。

    :::c
    struct PageInfo *
    page_lookup(pde_t *pgdir, void *va, pte_t **pte_store)
    {
        // Fill this function in
        pte_t *pte = pgdir_walk(pgdir, va, 0);//0表示当va不存在时，不会创建新页表，只用于查询

        if (pte == NULL || !(*pte & PTE_P))
            return NULL;

        if (pte_store != NULL)
            *pte_store = pte;
        return pa2page(PTE_ADDR(*pte));
    }

####3. page_remove
移除虚拟地址va对应的物理页的映射，使用上面的page_lookup先找到对应的物理页pages[]，
然后减少该物理页pages[]的引用计数，如果为0，则会加入空闲物理页表，


    :::c
    void
    page_remove(pde_t *pgdir, void *va)
    {
        // Fill this function in
        pte_t *pte;
        struct PageInfo *pg = page_lookup(pgdir, va, &pte);

        if (pg == NULL)
            return;
        page_decref(pg);
        *pte = 0;
        tlb_invalidate(pgdir, va);
    }

####4. page_insert
将物理页pages[]映射到虚拟地址va。先使用pgdir_walk（查看返回的PTE）查找该va是否
已经有物理页映射，则先使用page_remove移除该映射，然后再建立新的映射；如果没有
映射（PTE=NULL），则再次调用pgdir_walk建立映射。


    :::c
    int
    page_insert(pde_t *pgdir, struct PageInfo *pp, void *va, int perm)
    {
        // Fill this function in
        pte_t *pte = pgdir_walk(pgdir, va, 0);
        physaddr_t ppa = page2pa(pp);

        if (pte != NULL) {
           if (*pte & PTE_P) 
               page_remove(pgdir, va);
           if (pp == page_free_list) 
               page_free_list = page_free_list->pp_link;
        }
        else {
            pte = pgdir_walk(pgdir, va, 1);
            if (pte == NULL) 
                return -E_NO_MEM;
        }
        *pte = ppa | PTE_P | perm;
        pp->pp_ref++;
        tlb_invalidate(pgdir, va);
        return 0;
    }

####5. boot_map_region
将虚拟地址空间[va,  va+size)映射到物理地址空间[pa,  pa+size)，va，pa，size都是页对齐的（4KB整数倍），
方法就是对每一页进行映射，这里遇到一个很蛋疼的bug就是无符号整形的溢出问题。


    :::c
    static void
    boot_map_region(pde_t *pgdir, uintptr_t va, size_t size, physaddr_t pa, int perm)
    {
        // Fill this function in
        assert(va%PGSIZE == 0);
        assert(pa%PGSIZE == 0);
        assert(size%PGSIZE == 0);
        pte_t *pte;

        for (; size > 0; size -= PGSIZE) {
            pte = pgdir_walk(pgdir, (void *)va, true);
            if (pte == NULL) {
                panic("failed to create\n");
            }
            if (*pte & PTE_P) {
                cprintf("va=%x, size=%d, pa=%x\n", va, size, pa);
                panic("remapping\n");
            }
            *pte = pa | PTE_P | perm;
            va += PGSIZE;
            pa += PGSIZE;
        }

    }

练习最后一部分的工作是利用boot_map_region完成虚拟地址空间（UTOP以上的虚拟地址空间）
和物理地址空间的映射，并且此后kernel的运行将使用新的页目录kern_pgdir，在mem_init中：
1) 将pages[]数组以只读方式映射到用户空间（用户虚拟地址空间），
注意此时pages这块物理内存有两份映射，一份是内核虚拟地址空间
pages[]的首地址，还有一份就是这个地址UPAGES：

     boot_map_region(kern_pgdir, UPAGES, ROUNDUP(npages*sizeof(struct PageInfo), PGSIZE), 
                PADDR(pages), PTE_U);
UPAGES：是用户的虚拟地址空间，PADDR(pages)是pages对应的物理地址；

2) 将bootstack对应的物理内存作为内核的栈，也就是要将bootstack的物理内存映射到
内核的stack虚拟地址空间[KSTACKTOP-KSTKSIZE, KSTACKTOP]：

    boot_map_region(kern_pgdir, KSTACKTOP-KSTKSIZE, KSTKSIZE, 
            PADDR(bootstack), PTE_W);

3) 将所有的物理内存[0,  2^32 - KERNBASE]映射到虚拟地址空间[KERNBASE,  2^32]
（这个是将所有物理内存映射到内核虚拟地址空间，与最开始的映射是一致的）：

    boot_map_region(kern_pgdir, KERNBASE, ~KERNBASE+1, 0x0, PTE_W);

现在新建立的虚拟地址与物理地址的映射如下：
注意的几点：

1）ULIM以上是内核的虚拟地址空间，一下是用户虚拟地址空间，这里用boot_map_region
映射时都设置了权限，确保以后的用户进程不会读写内核虚拟地址空间；

2）[UTOP,  ULIM]之间的地址空间是是内核和用户都能读的，但不能写，
这段空间是用于将内核的一些数据结构expose 给用户进程使用，如pages数组。如何实现这一点呢？
就是将内核的那些需要暴露给用户的数据的物理内存地址映射到该区域即可，同时设置用户读权限；

3） ULIM以下是用户虚拟地址空间，要注意的是pages数组所在的物理内存既映射到了内核的
地址空间，同时又映射到了用户地址空间，只不过用户只有只读权限；


    /*
     * Virtual memory map:                                Permissions
     *                                                    kernel/user
     *
     *    4 Gig -------->  +------------------------------+
     *                     |                              | RW/--
     *                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     *                     :              .               :
     *                     :              .               :
     *                     :              .               :
     *                     |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~| RW/--
     *                     |                              | RW/--
     *                     |   Remapped Physical Memory   | RW/--
     *                     |                              | RW/--
     *    KERNBASE, ---->  +------------------------------+ 0xf0000000      --+
     *    KSTACKTOP        |     CPU0's Kernel Stack      | RW/--  KSTKSIZE   |
     *                     | - - - - - - - - - - - - - - -|                   |
     *                     |      Invalid Memory (*)      | --/--  KSTKGAP    |
     *                     +------------------------------+                   |
     *                     |     CPU1's Kernel Stack      | RW/--  KSTKSIZE   |
     *                     | - - - - - - - - - - - - - - -|                 PTSIZE
     *                     |      Invalid Memory (*)      | --/--  KSTKGAP    |
     *                     +------------------------------+                   |
     *                     :              .               :                   |
     *                     :              .               :                   |
     *    MMIOLIM ------>  +------------------------------+ 0xefc00000      --+
     *                     |       Memory-mapped I/O      | RW/--  PTSIZE
     * ULIM, MMIOBASE -->  +------------------------------+ 0xef800000
     *                     |  Cur. Page Table (User R-)   | R-/R-  PTSIZE
     *    UVPT      ---->  +------------------------------+ 0xef400000
     *                     |          RO PAGES            | R-/R-  PTSIZE
     *    UPAGES    ---->  +------------------------------+ 0xef000000
     *                     |           RO ENVS            | R-/R-  PTSIZE
     * UTOP,UENVS ------>  +------------------------------+ 0xeec00000
     * UXSTACKTOP -/       |     User Exception Stack     | RW/RW  PGSIZE
     *                     +------------------------------+ 0xeebff000
     *                     |       Empty Memory (*)       | --/--  PGSIZE
     *    USTACKTOP  --->  +------------------------------+ 0xeebfe000
     *                     |      Normal User Stack       | RW/RW  PGSIZE
     *                     +------------------------------+ 0xeebfd000
     *                     |                              |
     *                     |                              |
     *                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     *                     .                              .
     *                     .                              .
     *                     .                              .
     *                     |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|
     *                     |     Program Data & Heap      |
     *    UTEXT -------->  +------------------------------+ 0x00800000
     *    PFTEMP ------->  |       Empty Memory (*)       |        PTSIZE
     *                     |                              |
     *    UTEMP -------->  +------------------------------+ 0x00400000      --+
     *                     |       Empty Memory (*)       |                   |
     *                     | - - - - - - - - - - - - - - -|                   |
     *                     |  User STAB Data (optional)   |                 PTSIZE
     *    USTABDATA ---->  +------------------------------+ 0x00200000        |
     *                     |       Empty Memory (*)       |                   |
     *    0 ------------>  +------------------------------+                 --+
     */



