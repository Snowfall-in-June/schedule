import schedule
import time
import datetime

# 测试基本调度功能
def test_basic_scheduling():
    print("=== 测试基本调度功能 ===")
    
    # 计数器
    count = 0
    
    def job():
        nonlocal count
        count += 1
        print(f"Job {count} executed at {datetime.datetime.now()}")
    
    # 每100毫秒执行一次
    schedule.every(100).milliseconds.do(job)
    
    # 运行5次
    end_time = time.time() + 2  # 运行2秒
    while time.time() < end_time:
        schedule.run_pending()
        time.sleep(0.01)
    
    print(f"基本调度测试完成，共执行 {count} 次")

# 测试at方法
def test_at_method():
    print("\n=== 测试at方法 ===")
    
    executed = False
    
    def job():
        nonlocal executed
        executed = True
        print(f"At job executed at {datetime.datetime.now()}")
    
    # 测试分钟级at方法
    now = datetime.datetime.now()
    next_minute = now.minute + 1
    if next_minute >= 60:
        next_minute = 0
    
    schedule.every().minute.at(f":{next_minute:02d}").do(job)
    
    # 运行1分钟
    end_time = time.time() + 60
    while time.time() < end_time and not executed:
        schedule.run_pending()
        time.sleep(1)
    
    if executed:
        print("At方法测试成功")
    else:
        print("At方法测试超时")

# 测试取消任务
def test_cancel_job():
    print("\n=== 测试取消任务 ===")
    
    count = 0
    
    def job():
        nonlocal count
        count += 1
        print(f"Cancel test job {count} executed")
    
    # 创建任务
    job_instance = schedule.every(200).milliseconds.do(job)
    
    # 运行一段时间
    end_time = time.time() + 1
    while time.time() < end_time:
        schedule.run_pending()
        time.sleep(0.01)
    
    # 取消任务
    schedule.cancel_job(job_instance)
    print("任务已取消")
    
    # 再次运行一段时间，应该不会有新的执行
    count_before_cancel = count
    end_time = time.time() + 1
    while time.time() < end_time:
        schedule.run_pending()
        time.sleep(0.01)
    
    if count == count_before_cancel:
        print("取消任务测试成功")
    else:
        print(f"取消任务测试失败，取消后仍执行了 {count - count_before_cancel} 次")

if __name__ == "__main__":
    print("开始测试任务调度功能...")
    test_basic_scheduling()
    test_cancel_job()
    print("测试完成！")
