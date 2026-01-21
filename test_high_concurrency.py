import schedule
import threading
import time
import datetime
import concurrent.futures

# 测试参数
TEST_DURATION = 10  # 测试持续时间（秒）
NUM_THREADS = 10  # 并发线程数
TASKS_PER_THREAD = 5  # 每个线程添加的任务数
TASK_INTERVAL = 0.1  # 任务执行间隔（秒）

# 测试数据
task_executions = {}
lock = threading.Lock()

# 任务函数
def test_task(task_id):
    current_time = datetime.datetime.now()
    with lock:
        if task_id not in task_executions:
            task_executions[task_id] = []
        task_executions[task_id].append(current_time)
    print(f"Task {task_id} ran at: {current_time.strftime('%H:%M:%S.%f')}")

# 线程函数：添加任务
def add_tasks(thread_id):
    for i in range(TASKS_PER_THREAD):
        task_id = f"{thread_id}-{i}"
        schedule.every(TASK_INTERVAL).seconds.do(test_task, task_id)
        time.sleep(0.01)  # 小延迟，避免任务添加过于集中

# 线程函数：执行任务调度
def run_scheduler():
    end_time = time.time() + TEST_DURATION
    while time.time() < end_time:
        schedule.run_pending()
        time.sleep(0.001)  # 1毫秒的小延迟，减少CPU占用

# 主测试函数
def run_test():
    print(f"Testing high concurrency scheduling with {NUM_THREADS} threads")
    print(f"Each thread adds {TASKS_PER_THREAD} tasks")
    print(f"Test duration: {TEST_DURATION} seconds\n")
    
    # 创建线程池
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS + 1) as executor:
        # 提交添加任务的线程
        add_task_futures = []
        for i in range(NUM_THREADS):
            future = executor.submit(add_tasks, i)
            add_task_futures.append(future)
        
        # 等待所有任务添加完成
        concurrent.futures.wait(add_task_futures)
        
        # 提交执行调度的线程
        scheduler_future = executor.submit(run_scheduler)
        
        # 等待测试完成
        scheduler_future.result()
    
    # 计算结果
    print("\nCalculating results...")
    total_tasks = NUM_THREADS * TASKS_PER_THREAD
    executed_tasks = len(task_executions)
    total_executions = sum(len(executions) for executions in task_executions.values())
    
    print(f"Total tasks created: {total_tasks}")
    print(f"Total tasks executed: {executed_tasks}")
    print(f"Total executions: {total_executions}")
    
    # 检查是否有任务丢失
    if executed_tasks == total_tasks:
        print("\n✓ All tasks were executed (no tasks lost)")
    else:
        print(f"\n✗ Some tasks were lost: {total_tasks - executed_tasks} tasks not executed")
    
    # 检查任务执行频率
    print("\nChecking task execution frequency...")
    expected_executions = int(TEST_DURATION / TASK_INTERVAL)
    for task_id, executions in task_executions.items():
        execution_count = len(executions)
        if execution_count < expected_executions * 0.8:
            print(f"✗ Task {task_id} executed only {execution_count} times (expected ~{expected_executions})")
        else:
            print(f"✓ Task {task_id} executed {execution_count} times")

if __name__ == "__main__":
    run_test()
