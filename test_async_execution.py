import schedule
import time
import datetime
import threading

# 测试参数
TEST_DURATION = 10  # 测试持续时间（秒）
LONG_RUNNING_TASK_DURATION = 3  # 长时间任务执行时间（秒）
LONG_TASK_INTERVAL = 5  # 长时间任务执行间隔（秒）
SHORT_TASK_INTERVAL = 0.5  # 短时间任务执行间隔（秒）
NUM_SHORT_TASKS = 3  # 短时间任务数量

# 测试数据
task_executions = {}
lock = threading.Lock()

# 长时间运行的任务函数
def long_running_task():
    task_id = "long_running"
    start_time = datetime.datetime.now()
    print(f"Long running task started at: {start_time.strftime('%H:%M:%S.%f')}")
    
    # 模拟长时间运行
    time.sleep(LONG_RUNNING_TASK_DURATION)
    
    end_time = datetime.datetime.now()
    with lock:
        if task_id not in task_executions:
            task_executions[task_id] = []
        task_executions[task_id].append(end_time)
    print(f"Long running task finished at: {end_time.strftime('%H:%M:%S.%f')}")

# 短时间运行的任务函数
def short_running_task(task_id):
    current_time = datetime.datetime.now()
    with lock:
        if task_id not in task_executions:
            task_executions[task_id] = []
        task_executions[task_id].append(current_time)
    print(f"Short task {task_id} ran at: {current_time.strftime('%H:%M:%S.%f')}")

# 主测试函数
def run_test():
    print(f"Testing asynchronous execution with long-running task")
    print(f"Long running task duration: {LONG_RUNNING_TASK_DURATION} seconds")
    print(f"Short task interval: {SHORT_TASK_INTERVAL} seconds")
    print(f"Number of short tasks: {NUM_SHORT_TASKS}")
    print(f"Test duration: {TEST_DURATION} seconds\n")
    
    # 创建调度器
    scheduler = schedule.Scheduler()
    
    # 添加长时间运行的任务
    scheduler.every(LONG_TASK_INTERVAL).seconds.do(long_running_task)
    
    # 添加短时间运行的任务
    for i in range(NUM_SHORT_TASKS):
        task_id = f"short-{i}"
        scheduler.every(SHORT_TASK_INTERVAL).seconds.do(short_running_task, task_id)
    
    # 运行测试
    end_time = time.time() + TEST_DURATION
    while time.time() < end_time:
        scheduler.run_pending()
        # 不使用time.sleep，确保run_pending()方法能够频繁调用
        # time.sleep(0.001)  # 1毫秒的小延迟，减少CPU占用
    
    # 关闭调度器
    scheduler.shutdown()
    
    # 计算结果
    print("\nCalculating results...")
    
    # 检查长时间任务
    if "long_running" in task_executions:
        long_running_count = len(task_executions["long_running"])
        print(f"Long running task executed {long_running_count} times")
    else:
        print("Long running task was not executed")
    
    # 检查短时间任务
    short_task_executions = {k: v for k, v in task_executions.items() if k.startswith("short-")}
    print(f"\nShort tasks executed:")
    total_short_executions = 0
    for task_id, executions in short_task_executions.items():
        execution_count = len(executions)
        total_short_executions += execution_count
        expected_executions = int(TEST_DURATION / SHORT_TASK_INTERVAL)
        print(f"Task {task_id}: {execution_count} times (expected ~{expected_executions})")
    
    # 检查是否有任务错过调度
    print("\nChecking if short tasks were missed...")
    all_tasks_executed = True
    for task_id in [f"short-{i}" for i in range(NUM_SHORT_TASKS)]:
        if task_id not in task_executions or len(task_executions[task_id]) < expected_executions * 0.8:
            print(f"✗ Task {task_id} may have missed executions")
            all_tasks_executed = False
        else:
            print(f"✓ Task {task_id} executed normally")
    
    if all_tasks_executed:
        print("\n✓ All short tasks executed normally during long-running task")
    else:
        print("\n✗ Some short tasks missed executions during long-running task")

if __name__ == "__main__":
    run_test()
