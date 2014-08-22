#coding=UTF-8
#mm_crawler
#Author:Yangheng
#Email:vip@jishuniu.com

import sys
import os
import re
import time
import socket
import Queue
import urllib,urllib2
import threading
import getopt
from optparse import OptionParser 


"""执行基本命令"""
#resOpt存储最大线程数，图片存储位置，爬取图片限制数
resOpt = []

#初始化my_help
def my_help():
	print "-h Get help" 
	print "-n Specify the number of concurrent threads（default = 10）"
	print "-o Specify a directory to store pictures（default:pics/）"
	print "-l Limiting the number of pictures(default:unlimit)"
	
#初始化基本命令
def init_command():
	parser = OptionParser()
	parser.add_option('-n', "--threads",dest = "threads",help = "Specify the number of concurrent threads" )
	parser.add_option('-o', "--output",dest = "output",help = "Specify a directory to store pictures")
	parser.add_option('-l', "--limit",dest = "limit",help = "Limiting the number of pictures")

	(options, args) = parser.parse_args()
	opts, args = getopt.getopt('h', [])
	
	for o in opts:
		if o in ('-h', '--help'):
			my_help()
	        sys.exit(1)

	if not options.threads:   #options.numbers表示并发线程数
		options.threads = 10    
	else:
		options.threads = int(options.threads)
		
	if not options.output:    #options.output表示图片存储位置
		options.output = 'pics/'
		
	if not options.limit:     #options.limit表示限制爬取的图片数量
		options.limit=''
		
	resOpt.append(options.threads)
	resOpt.append(options.output)
	resOpt.append(options.limit)


"""获取网站各层页面链接"""
#模拟浏览器获取页面并解析页面内容
def user_agent(url):
	req_header = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
	req_timeout = 200
	try:
		req = urllib2.Request(url,None,req_header)
		page = urllib2.urlopen(req,None,req_timeout)
		userhtml = page
	except urllib2.URLError as e:
		print e.message
	except socket.timeout as e:
		user_agent(url)
	return userhtml.read()

spageList = []      #二级页面地址
sspageList = []     #[可获取小图图片]
tpageList = []      #三级页面首页地址
ttpageList = []     #[可获取大图图片]	

#编译正则表达式（反复调用编译比较耗时，只编译一次能减少运行时间）
ssupageHtml = re.compile(r'共(\d{4})套图片')
tupageHtml = re.compile(r'a href="(/mm/\w{5,9}/\w{1,100}.html)" title=')
ttupageHtml = re.compile(r'</span>/(\w{1,3})</strong>')
supageHtml = re.compile(r'img border="0" src="(http://\w{0,2}img\d{1}.meimei22.com/pic/\w{5,9}/\d{4}-\d{1,2}-\d{1,2}/\d{1}/\w{1,2}.jpg)')
bupageHtml = re.compile(r'arrayImg...="(http://\w{1,2}img1.meimei22.com/big/\w{5,9}/\d{4}-\d{1,2}-\d{1,2}/\d{1,2}/\w{1,100}.jpg)"')

#（第一层）base_url根页面地址
base_url = 'http://www.22mm.cc'

#（第二层）spageList二级页面地址（四个）
def get_spageList():
	msumCnt = 0	
	mpageList = ['/mm/qingliang/', '/mm/jingyan/', '/mm/bagua/', '/mm/suren/']
	for m in range(len(mpageList)):
		spageList.append(base_url + mpageList[m])
		msumCnt += 1200
		if msumCnt > imageLimit:
			break
		
#（第三层）sspageList二级页面分页地址[可获取小图图片]
def get_sspageList():
	global spageList
	ssumCnt = 0
	get_spageList()
	for i in range(len(spageList)):
		sspageList.append(spageList[i])
		sscurPage = spageList[i]
		#获取二级页面分页数spageCnt
		sspageHtml = user_agent(sscurPage)		
		spageCnt = int(re.findall(ssupageHtml, sspageHtml)[0])
		spageCnt /= 35
		#获取分页地址
		for j in range(2,spageCnt+1):
			sspageList.append(spageList[i]+'index_%d.html' %j)
			ssumCnt += 35
			if ssumCnt > imageLimit:
				break
		ssumCnt += 1
		if ssumCnt > imageLimit:
			break
	spageList = []

#（第四层）tpageList三级页面首页地址
def get_tpageList():
	tsumCnt = 5500
	get_sspageList()
	for h in range(len(sspageList)):
		tcurPage = sspageList[h]
		tpageHtml = user_agent(tcurPage)		
		tspageHtml = re.findall(tupageHtml,tpageHtml)
		for k in range(len(tspageHtml)):
			tpageList.append(base_url + tspageHtml[k])
			tsumCnt += 8
			if tsumCnt > imageLimit:
				break
		if tsumCnt > imageLimit:
			break
			
#（第五层）ttpageList三级页面分页地址[可获取大图图片]
def get_ttpageList():
	global tpageList
	get_tpageList()	
	ttsumCnt = 5500
	for s in range(len(tpageList)):
		ttpageList.append(tpageList[s])
		ttcurPage = tpageList[s]
		#获取三级页面分页数spageCnt
		ttpageHtml = user_agent(ttcurPage)		
		tpageCnt = int(re.findall(ttupageHtml,ttpageHtml)[0])
		#获取分页地址
		for d in range(2, tpageCnt+1):
			ttpageList.append(ttcurPage[:-5]+'-%s.html' %d)
			ttsumCnt += 1
			if ttsumCnt > imageLimit:
				break
		if ttsumCnt > imageLimit:
			break
	tpageList = []


"""获取图片URL"""
#获取图片链接[非相关图片已经筛选掉]
smallimageList = []      #小图图片URL
bigimageList = []	      #大图图片URL

#获取相关小图图片链接
def get_smallimageList():
	global sspageList
	get_sspageList()
	for m in range(len(sspageList)):
		spageHtml = user_agent(sspageList[m])	
		smallimageUrl = re.findall(supageHtml,spageHtml)
		for x in smallimageUrl:
			smallimageList.append(x)
	sspageList = []

#获取相关大图图片链接
def get_bigimageList():	
	global ttpageList
	get_ttpageList()	
	for n in range(len(ttpageList)):
		bpageHtml = user_agent(ttpageList[n])	 
		bigimageUrl = re.findall(bupageHtml,bpageHtml)
		for y in bigimageUrl:
			bigimageList.append(y)
	ttpageList = []
	
"""利用一个工作线程池下载图片"""
Qin = Queue.Queue()
Qout = Queue.Queue()
Qerr = Queue.Queue()
Pool = []

def report_error():
	Qerr.put(sys.exc_info()[:2])

def get_all_from_queue(Q):
	try:
		while True:
			yield Q.get_nowait()
	except Queue.Empty:
		raise StopIteration
		
#工作主循环		
def do_work_from_queue():
	while True:
		command, item, nums, downloadPath= Qin.get()
		if command == 'stop':
			break
		try:
			# 模拟工作线程的工作
			if command == 'process':
				urllib.urlretrieve(item , downloadPath + 'mmIMG%s.jpg' % nums) 
				result = "mmIMG%s.jpg" % nums+" has downloaded!"
				
			else:
				raise ValueError, 'Unkonwn command %r' % command
		except:
			#报告所有错误
			report_error()
		else:
			Qout.put(result)
		
#创建一个N线程的池子，使所有线程成为守护线程，启动所有线程
def make_and_start_thread_pool(number_of_threads_in_pool, daemons = True):
	for i in range(number_of_threads_in_pool):
		new_thread = threading.Thread(target = do_work_from_queue)
		new_thread.setDaemon(daemons)
		Pool.append(new_thread)
		new_thread.start()

def request_work(data, nums, downloadPath, command = 'process'):
	Qin.put((command, data, nums, downloadPath))
	
def get_result():
	return Qout.get()	

#输出结果	
def show_all_results():
	for result in get_all_from_queue(Qout):
		print result

#输出所有的错误		
def show_all_errors():
	for etyp, err in get_all_from_queue(Qerr):
		print 'Error:', etyp, err

#停止并释放线程池		
def stop_and_free_thread_pool():
	#首先要求所有线程停止
	for i in range(len(Pool)):
		request_work(None, None, None, 'stop')
	#然后等待每个线程终止
	for existing_thread in Pool:
		existing_thread.join()
	#清除线程池
	del Pool[:]

#下载图片
def download_image():
	global bigimageList,smallimageList
	#如果不存在图片储存的路径，则创建一个路径
	if not os.path.isdir(downloadPath):
		os.mkdir('%s' %(downloadPath))
		
	#多线程下载
	nums = 0
	#优先下载小图
	get_smallimageList()
	for imgUrl in smallimageList:
		if nums == imageLimit:
			break
		request_work(imgUrl, nums, downloadPath)
		if len(smallimageList) > 500:
			smallimageList = []
		nums += 1	     
	
	#小图总数没有达到限制下载输，则下载大图			
	if nums < imageLimit:
		get_bigimageList()
		for imgUrl in bigimageList:
			if nums == imageLimit:
				break
			request_work(imgUrl, nums, downloadPath)
			if len(bigimageList) > 500:
				bigimageList = []
			nums += 1  
	
	make_and_start_thread_pool(threadsLimit)
	stop_and_free_thread_pool()
	show_all_results()
	show_all_errors()
	
	print "##########################"
	print "已完成%s张图片的下载！" % (nums)

		
"""完成爬虫任务"""
if __name__ == "__main__":
	init_command()
	threadsLimit = int(resOpt[0])     #最大线程数
	downloadPath = resOpt[1]          #图片存储位置
	if resOpt[2] == '':
		imageLimit = 1000             #为空时默认80000张（网站不重复图片不超过80000张），为测试方便设为1000张
	else:
		imageLimit = int(resOpt[2])   #图片下载限制数
	print "##########################"
	print "等待下载："
	print "##########################"
	download_image()
	print "##########################"	
	print "下载完成"
	print "##########################"
