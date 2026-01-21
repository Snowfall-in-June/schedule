import schedule
import time
import datetime

# 测试参数
TEST_INTERVAL_MS = 100  # 100毫秒
TEST_RUNS = 10  # 运行10次

# 测试数据
run_times = []
expected_times = []

# 任务函数
def test_job():
    current_time = datetime.datetime.now()
    run_times.append(current_time)
    print(f"Job ran at: {current_time.strftime('%H:%M:%S.%f')}")

# 主测试函数
def run_test():
    print(f"Testing millisecond scheduling with interval: {TEST_INTERVAL_MS}ms")
    print(f"Expected to run {TEST_RUNS} times\n")
    
    # 计算预期运行时间
    start_time = datetime.datetime.now()
    for i in range(TEST_RUNS):
        expected_time = start_time + datetime.timedelta(milliseconds=TEST_INTERVAL_MS * (i + 1))
        expected_times.append(expected_time)
    
    # 调度任务
    schedule.every(TEST_INTERVAL_MS).milliseconds.do(test_job)
    
    # 运行测试
    run_count = 0
    while run_count < TEST_RUNS:
        schedule.run_pending()
        time.sleep(0.001)  # 1毫秒的小延迟，减少CPU占用
        run_count = len(run_times)
    
    # 计算偏差
    print("\nCalculating deviations...")
    deviations = []
    for i, (actual, expected) in enumerate(zip(run_times, expected_times)):
        deviation = (actual - expected).total_seconds() * 1000  # 转换为毫秒
        deviations.append(deviation)
        print(f"Run {i+1}: Deviation = {deviation:.3f}ms")
    
    # 统计结果
    if deviations:
        avg_deviation = sum(deviations) / len(deviations)
        max_deviation = max(deviations, key=abs)
        print(f"\nSummary:")
        print(f"Average deviation: {avg_deviation:.3f}ms")
        print(f"Maximum deviation: {max_deviation:.3f}ms")
        
        # 判断准确性
        if abs(avg_deviation) < 10 and abs(max_deviation) < 50:
            print("\n✓ Millisecond scheduling is accurate!")
        else:
            print("\n✗ Millisecond scheduling may not be accurate enough.")

if __name__ == "__main__":
    run_test()
