Title: How to use Pelican to bulid blog on github.io
Date: 2015-11-13
Category: python
Tags: pelican blog python virtualenv githubio
Author: jin

##1. virtualenv的使用
python开发的常用工具，使用这个工具可以隔离本项目依赖的环境设置，这样就能避免干扰其他项目的环境变量设置。virtualenv的使用参考：http://docs.python-guide.org/en/latest/dev/virtualenvs/.
常用命令：
virtualenv venv：建立一个虚拟环境，会在当前目录中建立一个venv的目录，里面包含了这个虚拟环境所有的配置信息；
virtualenv -p /usr/bin/python2.7 venv：指定venv环境使用python解释器；
source venv/bin/activate：激活该虚拟环境，每次使用该命令进入虚拟环境；
deactivate：退出虚拟环境；

##2. 安装pelican
这个可在虚拟环境下安装，也可以就在本机环境下安装，
    $: sudo pip install pelican
安装markdown
    $: sudo pip install Markdown

##3. Run Pelican
第一次使用的话使用下面的命令
    $: pelican-quickstart
然后会出现一系列的问题，按照要求填好即可。此时会在当前目录生成下面几个文件：
.
├── Makefile
├── content  #用于添加自己的内容
├── develop_server.sh
├── fabfile.py
├── output  #这是pelican根据content生成的html文件等（用make html命令）
├── pelicanconf.py   #配置文件
└── publishconf.py

##4. Use Pelican to Generate html
用markdonw语法写一篇blog：test.md，然后将其放在content中，使用下面命令让pelican生成对应的html文件，放在output目录中：
    $: make  html 
然后使用下面命令在本地观察bolg效果：
    $: make serve
在本地使用http://localhost:8000来访问，即可查看效果。
修改页面时可使用make regegerate，也可以使用make devserve（相当于make regenerate & make serve）。
本地测试完毕后，使用下面命令来停止server：
    $: ./develop_server.sh stop

##5. Publish on github.io
先要在github上申请username.github.io，具体申请方法就不多说了，官网非常详细。那么到现在我们如何将pelican生成的blog放到github上呢？只需把output里面的内容push到username.github.io里面即可。所以一种方法就是在output建立repo，然后将remote repo设为username.github.io即可。如下：
    $: cd output/
    $: git init
    $: git remote add origin https://github.com/username/username.github.io
    $: git add -A
    $: git commit -m 'first commit'
    $: git push origin master
现在大功告成，可以访问username.github.io查看效果。
另外有些要注意的事项：
在publishconf.py 中，将设置改为如下，否则使用pelican命令时会删除output目录：
DELETE_OUTPUT_DIRECTORY = False

参考官方文档：http://docs.getpelican.com/en/3.1.1/getting_started.html#installing-pelican
