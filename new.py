import requests
import re
import subprocess
import concurrent.futures
import time
from collections import defaultdict

def download_file(url):
    """下载原始配置文件"""
    print("正在下载配置文件...")
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def remove_first_two_lines(content):
    """删除前两行"""
    lines = content.split('\n')
    return '\n'.join(lines[2:])

def remove_multicast_chars(content):
    """删除所有-组播字符"""
    return content.replace('-组播', '')

def parse_groups(content):
    """解析分组和频道信息"""
    groups = {}
    current_group = None
    current_channels = []
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if '#genre#' in line:
            # 保存上一个分组
            if current_group and current_channels:
                groups[current_group] = current_channels
            
            # 开始新分组
            current_group = line.split(',#genre#')[0]
            current_channels = []
        elif current_group and ',' in line:
            # 频道行
            parts = line.split(',', 1)
            if len(parts) == 2:
                channel_name, channel_url = parts
                current_channels.append((channel_name, channel_url))
    
    # 保存最后一个分组
    if current_group and current_channels:
        groups[current_group] = current_channels
    
    return groups

def check_stream(url, timeout=5):
    """使用ffprobe检测流是否有效"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-i", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout + 2
        )
        return b"codec_type" in result.stdout
    except Exception:
        return False

def test_group_first_channel(group_name, channels):
    """测试分组第一个频道的有效性"""
    if not channels:
        return group_name, False
    
    first_channel_name, first_channel_url = channels[0]
    print(f"测试分组 '{group_name}' 的第一个频道: {first_channel_name}")
    
    is_valid = check_stream(first_channel_url)
    if is_valid:
        print(f"✓ 分组 '{group_name}' 有效")
    else:
        print(f"✗ 分组 '{group_name}' 无效")
    
    return group_name, is_valid

def test_groups(groups, max_workers=10):
    """测试所有分组的有效性"""
    print(f"🚀 启动多线程检测（共 {len(groups)} 个分组）...")
    valid_groups = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有检测任务
        future_to_group = {
            executor.submit(test_group_first_channel, group_name, channels): group_name 
            for group_name, channels in groups.items()
        }
        
        # 收集结果
        for future in concurrent.futures.as_completed(future_to_group):
            group_name, is_valid = future.result()
            if is_valid:
                valid_groups[group_name] = groups[group_name]
    
    print(f"✅ 检测完成，有效分组共 {len(valid_groups)} 个")
    return valid_groups

def process_valid_channels(valid_groups):
    """处理有效频道，生成平表格式"""
    flat_channels = []
    
    for group_name, channels in valid_groups.items():
        for channel_name, channel_url in channels:
            # 在URL后添加$运营商分组
            processed_url = f"{channel_url}${group_name}"
            flat_channels.append((channel_name, processed_url, group_name))
    
    return flat_channels

def recategorize_channels(channels):
    """按照自定义规则重新分类频道"""
    categories = {
        "央视": [],
        "卫视": [],
        "地方台": [],
        "电影": [],
        "体育": [],
        "少儿": [],
        "其他": []
    }
    
    # 分类规则
    for channel_name, channel_url, group_name in channels:
        channel_name_lower = channel_name.lower()
        
        if any(keyword in channel_name for keyword in ['CCTV', '央视', '中央']):
            categories["央视"].append((channel_name, channel_url))
        elif any(keyword in channel_name_lower for keyword in ['卫视', 'tv']):
            categories["卫视"].append((channel_name, channel_url))
        elif any(keyword in channel_name for keyword in [
            '北京', '上海', '广东', '湖南', '浙江', '江苏', '四川', '重庆', 
            '天津', '河北', '山西', '辽宁', '吉林', '黑龙江', '安徽', 
            '福建', '江西', '山东', '河南', '湖北', '广西', '海南', '贵州',
            '云南', '陕西', '甘肃', '青海', '台湾', '香港', '澳门'
        ]):
            categories["地方台"].append((channel_name, channel_url))
        elif any(keyword in channel_name_lower for keyword in ['电影', '影院', '剧场']):
            categories["电影"].append((channel_name, channel_url))
        elif any(keyword in channel_name_lower for keyword in ['体育', '足球', '篮球', '赛事']):
            categories["体育"].append((channel_name, channel_url))
        elif any(keyword in channel_name_lower for keyword in ['少儿', '卡通', '动画', '动漫']):
            categories["少儿"].append((channel_name, channel_url))
        else:
            categories["其他"].append((channel_name, channel_url))
    
    return categories

def save_categorized_channels(categories, output_file):
    """保存重新分类后的频道到文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for category, channels in categories.items():
            if channels:  # 只输出有频道的分类
                f.write(f"{category},#genre#\n")
                for channel_name, channel_url in channels:
                    f.write(f"{channel_name},{channel_url}\n")
                f.write("\n")
    
    print(f"处理完成！结果已保存到: {output_file}")

def save_flat_channels(channels, output_file):
    """保存平表格式的频道列表"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for channel_name, channel_url, group_name in channels:
            f.write(f"{channel_name},{channel_url}\n")
    
    print(f"平表格式已保存到: {output_file}")

def main():
    # 配置文件URL
    url = "https://raw.githubusercontent.com/q1017673817/iptvz/main/zubo_all.txt"
    
    try:
        # 1. 下载文件
        content = download_file(url)
        
        # 2. 删除前两行
        content = remove_first_two_lines(content)
        
        # 3. 删除-组播字符
        content = remove_multicast_chars(content)
        
        # 4. 解析原始分组
        original_groups = parse_groups(content)
        print(f"找到 {len(original_groups)} 个原始分组")
        
        # 5. 测试分组有效性
        valid_groups = test_groups(original_groups)
        
        # 6. 处理有效频道，生成平表
        flat_channels = process_valid_channels(valid_groups)
        print(f"有效频道数量: {len(flat_channels)}")
        
        # 7. 保存平表格式
        flat_output_file = "flat_iptv_list.txt"
        save_flat_channels(flat_channels, flat_output_file)
        
        # 8. 重新分类
        categories = recategorize_channels(flat_channels)
        
        # 9. 保存分类格式
        categorized_output_file = "categorized_iptv_list.txt"
        save_categorized_channels(categories, categorized_output_file)
        
        # 打印统计信息
        total_channels = sum(len(channels) for channels in categories.values())
        print(f"\n📊 统计信息:")
        print(f"总频道数: {total_channels}")
        for category, channels in categories.items():
            if channels:
                print(f"{category}: {len(channels)} 个频道")
                
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 检查ffprobe是否可用
    try:
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
        print("✅ ffprobe 可用，将使用ffprobe进行流媒体检测")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ 警告: ffprobe 未找到或不可用，请安装ffmpeg")
        print("Ubuntu/Debian: sudo apt install ffmpeg")
        print("macOS: brew install ffmpeg")
        print("Windows: 从 https://ffmpeg.org/download.html 下载")
        exit(1)
    
    main()