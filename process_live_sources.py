import requests
import re
from collections import defaultdict
import os
from datetime import datetime
import sys
import traceback

def debug_log(message):
    """调试日志函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def fetch_original_data(url):
    """从GitHub获取原始数据"""
    try:
        debug_log("开始获取原始数据...")
        # 将GitHub页面链接转换为原始内容链接
        raw_url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        debug_log(f"转换后的URL: {raw_url}")
        
        response = requests.get(raw_url, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        debug_log(f"成功获取数据，长度: {len(response.text)} 字符")
        return response.text
    except Exception as e:
        debug_log(f"获取数据失败: {e}")
        return None

def parse_original_data_skip_first_two_lines(content):
    """解析原始数据，跳过前两行"""
    debug_log("开始解析原始数据（跳过前两行）...")
    lines = content.split('\n')
    
    # 跳过前两行
    if len(lines) > 2:
        lines = lines[2:]
        debug_log("已跳过前两行")
    else:
        debug_log("数据行数不足，未跳过任何行")
    
    result = []
    current_region = ""
    line_count = 0
    valid_channels = 0
    
    for line in lines:
        line_count += 1
        original_line = line.strip()
        line = original_line
        
        if not line:
            continue
            
        # 多种可能的地区行格式
        if '#genre#' in line.lower():
            try:
                # 尝试多种格式的地区行
                if line.startswith('"') and line.endswith('"'):
                    # 格式: "地区运营商","#genre#"
                    parts = line.split(',', 1)
                    if len(parts) >= 1:
                        current_region = parts[0].strip('"')
                        debug_log(f"发现地区分类: {current_region}")
                else:
                    # 格式: 地区运营商,#genre#
                    parts = line.split(',', 1)
                    if len(parts) >= 1:
                        current_region = parts[0].strip().strip('"')
                        debug_log(f"发现地区分类: {current_region}")
            except Exception as e:
                debug_log(f"解析地区行失败 (第{line_count}行): {e}")
            continue
            
        # 多种可能的频道行格式
        try:
            # 跳过明显不是频道行的内容
            if not line or '#genre#' in line.lower() or len(line) < 5:
                continue
                
            # 尝试多种频道行格式
            channel_name = ""
            channel_url = ""
            
            # 格式1: "频道名称","地址"
            if line.startswith('"') and line.count('"') >= 4:
                parts = line.split('","')
                if len(parts) >= 2:
                    channel_name = parts[0].strip('"')
                    channel_url = parts[1].strip('"')
            
            # 格式2: 频道名称,地址
            elif ',' in line and not channel_name:
                parts = line.split(',', 1)
                if len(parts) >= 2:
                    channel_name = parts[0].strip().strip('"')
                    channel_url = parts[1].strip().strip('"')
            
            # 验证并保存有效的频道
            if (channel_name and channel_url and current_region and 
                not channel_url.endswith('#genre#') and
                not channel_name.endswith('#genre#') and
                ('http' in channel_url.lower() or 'rtmp' in channel_url.lower() or 
                 'rtsp' in channel_url.lower() or 'm3u8' in channel_url.lower())):
                
                new_line = f'"{channel_name}","{channel_url}"$"{current_region}"'
                result.append(new_line)
                valid_channels += 1
                
                if valid_channels <= 3:  # 只记录前3个成功解析的频道用于调试
                    debug_log(f"成功解析频道: {channel_name}")
                    
        except Exception as e:
            debug_log(f"解析频道行失败 (第{line_count}行): {e}")
            continue
    
    debug_log(f"解析完成，共找到 {len(result)} 个频道")
    return result

# 简化的分类映射
CATEGORY_MAPPING = {
    "央视,#genre#": [
        "CCTV-1综合", "CCTV-2财经", "CCTV-3综艺", "CCTV-4中文国际", "CCTV-5体育", 
        "CCTV-5+体育赛事", "CCTV-6电影", "CCTV-7国防军事", "CCTV-8电视剧", "CCTV-9纪录", 
        "CCTV-10科教", "CCTV-11戏曲", "CCTV-12社会与法", "CCTV-13新闻", "CCTV-14少儿", 
        "CCTV-15音乐", "CCTV-16奥林匹克", "CCTV-16奥林匹克4K", "CCTV-17农业农村", 
        "CCTV-4欧洲", "CCTV-4美洲", "CCTV-4K", "CCTV-8K", "CCTV风云剧场", "CCTV怀旧剧场", 
        "CCTV第一剧场", "CCTV风云足球", "CCTV央视台球", "CCTV高尔夫·网球", "CCTV风云音乐", 
        "CCTV央视文化精品", "CCTV卫生健康", "CCTV电视指南", "CCTV兵器科技", "CCTV女性时尚", 
        "CCTV世界地理", "CHC家庭影院", "CHC动作电影", "CHC影迷电影", "中央新影-中学生", 
        "中央新影-老故事", "中央新影-发现之旅", "CGTN", "CGTN-纪录", "CGTN-法语", 
        "CGTN-俄语", "CGTN-西班牙语", "CGTN-阿拉伯语", "中国教育-1", "中国教育-2", 
        "中国教育-4", "早期教育"
    ],
    "卫视,#genre#": [
        "山东卫视", "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视", "深圳卫视", 
        "广东卫视", "大湾区卫视", "广西卫视", "东南卫视", "海南卫视", "河北卫视", "河南卫视", 
        "湖北卫视", "江西卫视", "四川卫视", "重庆卫视", "贵州卫视", "云南卫视", "天津卫视", 
        "安徽卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视", "内蒙古卫视", "宁夏卫视", "山西卫视", 
        "陕西卫视", "甘肃卫视", "青海卫视", "新疆卫视", "西藏卫视", "三沙卫视", "兵团卫视", 
        "延边卫视", "安多卫视", "康巴卫视", "农林卫视", "海峡卫视", "山东教育卫视"
    ],
    "4K,#genre#": [
        "北京卫视4K", "广东卫视4K", "深圳卫视4K", "山东卫视4K", "湖南卫视4K", "浙江卫视4K", 
        "江苏卫视4K", "东方卫视4K", "四川卫视4K"
    ],
    "国际,#genre#": [
        "凤凰卫视", "凤凰资讯", "凤凰香港", "凤凰电影", "星空卫视", "Channel [V]"
    ],
    "数字,#genre#":[
"求索纪录","求索科学","求索生活","求索动物","纪实人文","金鹰纪实","纪实科教","睛彩青少","睛彩竞技","睛彩篮球","睛彩广场舞","魅力足球","五星体育""劲爆体育","快乐垂钓","茶频道","先锋乒羽","天元围棋","汽摩","梨园频道","文物宝库","武术世界","哒啵赛事","哒啵电竞","黑莓电影","黑莓动画","乐游","生活时尚","都市剧场","欢笑剧场","游戏风云","金色学堂","动漫秀场","新动漫","卡酷少儿","金鹰卡通","优漫卡通","哈哈炫动","嘉佳卡通","中国交通","中国天气","华数4K","华数星影","华数动作影院","华数喜剧影院","华数家庭影院","华数经典电影","华数热播剧场","华数碟战剧场","华数军旅剧场","华数城市剧场","华数武侠剧场","华数古装剧场","华数魅力时尚","华数少儿动画","华数动画","iHOT爱喜剧","iHOT爱科幻","iHOT爱院线","iHOT爱悬疑","iHOT爱历史","iHOT爱谍战","iHOT爱旅行","iHOT爱幼教","iHOT爱玩具","iHOT爱体育","iHOT爱赛车","iHOT爱浪漫","iHOT爱奇谈","iHOT爱科学","iHOT爱动漫"
    ],
    "山东,#genre#":[
"山东齐鲁频道","山东体育频道","山东农科频道","山东新闻频道","山东少儿频道","山东文旅频道","山东综艺频道","山东生活频道","山东居家购物","济南新闻综合","济南教育频道","济南都市","济南生活","济南文旅教育","济南娱乐","济南少儿","济南鲁中","历城综合","长清新闻","济阳综合频道","平阴综合频道","商河综合","QTV-1","QTV-2","QTV-3","QTV-4","QTV-5","崂山综合","黄岛综合","黄岛生活","胶州综合","平度新闻综合","莱西综合频道","淄博新闻综合","淄博影视频道","淄博文旅","淄博民生","张店综合","淄川新闻","周村新闻","桓台综合","高青综合","沂源新闻","东营新闻","东营公共","广饶新闻","烟台新闻综合","烟台公共","烟台经济科教","烟台影视频道","牟平新闻","牟平生活","蓬莱新闻","龙口综合","招远综合","栖霞综合","海阳综合","海阳综艺","长岛综合","潍坊新闻综合","潍坊经济生活","潍坊影视综艺","潍坊科教文旅","潍坊高新区","青州综合频道","青州文化旅游","诸城新闻","寿光新闻","寿光蔬菜","安丘综合频道","高密综合","昌邑综合频道","昌乐综合频道","临朐综合","济宁综合频道","济宁生活","济宁公共","济宁高新","任城-1","任城-2","兖州新闻频道","曲阜综合频道","邹城综合频道","鱼台新闻","鱼台生活","嘉祥综合","梁山综合频道","汶上综合","泰山电视","肥城综合","岱岳有线","新泰综合频道","新泰乡村频道","宁阳综合频道","宁阳2","东平综合频道","威海新闻","威海都市生活","文登TV-1","荣成综合频道","乳山综合频道","日照新闻","日照科教","日照公共","莒县综合","日照岚山频道","河东综合","沂水综合","沂水生活","兰陵综合频道","兰陵公共","五莲新闻","蒙阴综合频道","临沭综合","莒南综合","德州新闻综合","德州经济生活","陵城综合频道","禹城综合频道","禹城综艺频道","宁津综合频道","齐河新闻频道","武城综合频道","武城综艺影视","平原综合频道","夏津新闻","夏津公共频道","临邑综合","聊城综合频道","聊城民生频道","茌平综合频道","临清综合","莘县综合频道","冠县综合","东阿综合","滨州综合频道","滨州民生","沾化综合频道","邹平新闻","惠民综合","阳信新闻综合","无棣综合频道","菏泽新闻","菏泽生活","定陶TV-1","单县综合频道","鄄城新闻","郓城综合频道","巨野新闻频道","东明新闻"
    ],
    "北京,#genre#":[
"北京IPTV4K超清","北京IPTV淘电影","北京IPTV淘剧场","北京IPTV淘精彩","北京IPTV淘娱乐","北京IPTV淘Baby","北京IPTV萌宠TV","北京IPTV重温经典","北京纪实科教","北京卡酷少儿","北京体育休闲","北京新闻","北京财经","北京生活","北京影视","北京文艺","北京青年","北京国际","朝阳区","通州区","门头沟区","房山区","密云区","延庆区"
    ],
    "上海,#genre#":[
"新视觉","上海新闻综合","第一财经","东方财经","东方影视","哈哈炫动","五星体育","劲爆体育","上海都市","上海教育","纪实人文","都市剧场","欢笑剧场","欢笑剧场4K","动漫秀场","乐游频道","法治天地","金色学堂","游戏风云","生活时尚","魔都眼","浦东","外语频道"
    ],
    "广东,#genre#":[
"广东体育FHD","广东体育HD","广东珠江FHD","广东珠江HD","广东影视HD","广东民生HD","广东经济科教FHD","广东经济科教HD","广东现代教育HD","广东新闻HD","大湾区卫视HD","岭南戏曲HD","嘉佳卡通HD","广东少儿HD","广东综艺4K","广州综合HD","广州新闻HD","广州影视HD","广州法治HD","南国都市4K","深圳都市HD","深圳电视剧HD","深圳财经生活HD","深圳体育健康HD","深圳少儿HD","深圳众创TV","深圳宝安频道HD","深圳龙岗HD"
    ],
    "四川,#genre#":[
"四川经济频道","四川文化旅游","四川新闻频道","四川影视文艺","四川星空购物","四川妇女儿童","四川科教频道","四川乡村","四川峨嵋电影","成都新闻综合","成都经济资讯","成都都市生活","成都影视文艺","成都公共","成都少儿","蓉城先锋"
    ],
    "重庆,#genre#":[
"重庆新闻","重庆影视","重庆文体娱乐","重庆新农村","重庆少儿","重庆社会与法","重庆红叶","重庆红岩文化","重庆汽摩","重庆移动","重广传媒","重庆时尚生活","重庆科教"
    ],
    "安徽,#genre#":[
"安徽经济生活","安徽影视频道","安徽农业科教","安徽国际频道","安徽公共频道","安徽综艺体育","合肥新闻频道","肥西新闻综合","黄山新闻综合","黄山文旅频道","旌德新闻综合","霍邱新闻综合","六安综合频道","六安社会生活","淮北新闻综合","淮北经济生活","淮南新闻综合","淮南民生频道","滁州新闻综合","滁州科教频道","滁州公共频道","蒙城新闻频道","南陵新闻综合","祁门综合频道","湾沚综合频道","繁昌新闻综合","桐城综合频道","太湖新闻综合","池州新闻综合","池州文教生活","义安新闻综合","阜阳新闻综合","阜阳生活频道","阜阳教育频道","阜阳都市文艺","泗县新闻频道","临泉新闻频道","阜南新闻综合","亳州综合频道","亳州农村频道","徽州新闻频道","蚌埠新闻综合","蚌埠生活频道","寿县新闻综合","屯溪融媒频道","芜湖新闻综合","芜湖生活频道","无为新闻频道","马鞍山新闻综合","马鞍山科教生活","安庆新闻综合","安庆经济生活","潜山综合频道","黄山区融媒","歙县综合频道","休宁新闻综合","黟县新闻综合","宣城综合频道","宣城文旅生活","广德新闻综合","广德生活频道","郎溪新闻频道","宁国新闻综合","铜陵新闻综合","铜陵教育科技","枞阳电视台","霍山综合频道","金寨综合频道","濉溪新闻频道","宿州新闻综合","宿州公共频道","宿州科教频道","萧县新闻综合","五河新闻综合","固镇新闻综合","界首综合频道","利辛新闻综合","涡阳新闻综合"
    ],
    "甘肃,#genre#":[
"甘肃文化影视","甘肃公共","甘肃都市","甘肃经济","甘肃少儿","金塔","酒钢电视","嘉峪关公共","嘉峪关综合","陇上生活","临夏新闻","临夏文旅","临夏经济"
    ],
    "江苏,#genre#":[
"江苏城市","江苏综艺","江苏休闲体育","江苏影视","优漫卡通","江苏新闻","江苏教育","江苏国际","江苏靓妆","江苏购物","南京新闻综合","南京十八·生活","南京教科","南京文旅纪录","南京影视","南京少儿"
    ],
    "河北,#genre#":[
"河北经济生活","河北都市","河北影视剧","河北少儿科教","河北文旅公共","河北农民","睛彩河北","河北杂技","河北三佳购物","石家庄新闻综合","石家庄文化娱乐","石家庄城市服务"
    ],
    "山西,#genre#":[
"黄河电视台","山西经济与科技","山西影视","山西社会与法治","山西文体生活","晋中综合频道","晋中公共频道","运城1台","运城2台","盐湖频道","清徐","朔州-1","朔州-2","孝义电视台","古交电视台","阳曲","太原1","太原2","太原3","太原4","太原5","太原教育","晋能控股","大同教育","阳泉-1新闻综合","阳泉-2科教"
    ],
    "广西,#genre#":[
"广西综艺旅游","广西影视频道","广西新闻频道","广西都市频道","广西国际频道","广西移动电视","南宁新闻综合","南宁影视娱乐","南宁公共频道","南宁文旅生活","柳州新闻","北海新闻","玉林新闻","贺州新闻","桂林新闻"
    ],
    "海南,#genre#":[
"海南公共频道","海南少儿频道","海南文旅频道","海南新闻频道","海南自贸频道"
    ],
    "湖南,#genre#":[
"湖南经视频道","湖南都市频道","湖南国际频道","湖南公共频道","湖南娱乐频道","湖南电影频道","湖南电视剧频道"
    ],
    "湖北,#genre#":[
"湖北公共新闻","湖北经视频道","湖北经视频道","湖北垄上频道","湖北影视频道","湖北生活频道","湖北生活频道","武汉新闻综合","武汉电视剧","武汉科技生活","武汉文体频道","武汉教育频道","阳新综合","房县综合","蔡甸综合"
    ],
    "江西,#genre#":[
"江西都市频道","江西经济生活","江西影视旅游","江西公共农业","江西少儿频道","江西新闻频道","江西教育频道"
    ],
    "黑龙江,#genre#":[
"黑龙江影视频道","黑龙江新闻法治","黑龙江少儿频道","黑龙江文体频道","黑龙江农业科教","黑龙江都市频道","哈尔滨新闻综合","哈尔滨生活频道","哈尔滨影视频道","齐齐哈尔新闻综合","齐齐哈尔经济法治","佳木斯新闻综合"
    ],
    "吉林,#genre#":[
"长影频道","吉林教育","吉林篮球","扶余电视台","延边TV1","延边TV2","TTV洮南1","农安综合","吉林科教","辽源新闻综合","辽源民生社会","松原综合频道","松原生活频道","白山新闻综合1","白山旅游生活2","四平1","四平2","TTV1","TTV2","TTV3","磐石综合频道","图门电视台","双辽"
    ],
    "辽宁,#genre#":[
"辽宁都市频道","辽宁影视剧频道","辽宁体育休闲","辽宁生活频道","辽宁教育青少","辽宁北方频道","辽宁公共频道","辽宁经济频道","沈阳新闻综合","辽河新闻综合","辽河文化生活"
    ],
    "内蒙古,#genre#":[
"内蒙古蒙语频道","内蒙古经济生活","内蒙古新闻综合","内蒙古文体娱乐","内蒙古农牧频道","内蒙古少儿频道","呼市新闻综合","呼市新闻综合","包头经济频道","包头生活服务","包头新闻综合","乌海新闻综合","乌海都市生活","赤峰新闻综合","赤峰经济服务","赤峰影视娱乐","通辽城市服务","通辽新闻综合","通辽蒙语频道","呼伦贝尔新闻综合","呼伦贝尔文化旅游","呼伦贝尔生活资讯","巴彦淖尔新闻综合","巴彦淖尔经济生活","巴彦淖尔影视娱乐","鄂尔多斯新闻综合","鄂尔多斯经济服务","鄂尔多斯蒙语频道","锡林郭勒1","锡林郭勒2","杭后电视台","达茂电视台","库伦电视台","丰镇电视台","突泉电视台","阿尔山电视台","托克托电视台","额济纳新闻综合","西乌电视台","准格尔综合频道","伊金霍洛旗综合","苏尼特左旗","苏尼特右旗","乌拉特前旗","乌拉特中旗","乌拉特后旗","乌盟经济生活","乌盟新闻综合","兴安新闻综合","兴安文化旅游","兴安影视娱乐","阿拉善新闻综合","XHTV","ELTV","五原","磴口","武川","扎兰屯","阿巴嘎","翁牛特","满洲里","阿右旗","正蓝旗","东乌旗","土左旗","太仆寺旗","科右中旗","正镶白旗","扎赉特旗","察右中旗","喀喇沁县","额尔古纳","和林格尔","克什克腾旗","内蒙古购物"
    ],
    "宁夏,#genre#":[
"宁夏公共频道","宁夏教育频道","宁夏经济频道","宁夏少儿频道","宁夏文旅频道","银川公共频道","银川生活频道","银川文体频道"
    ],
    "青海,#genre#":[
"青海都市","青海经视","西宁新闻综合","西宁生活服务","海东综合频道","海北电视台","海西电视台"
    ],
    "陕西,#genre#":[
"陕西新闻资讯","陕西都市青春","陕西体育休闲","陕西农林卫视","陕西西部电影","陕西秦腔频道","陕西银铃频道","西安新闻综合","西安都市频道","西安商务资讯","西安戏剧影视","西安丝路频道","西安教育频道","西安乐购购物"
    ],
    "天津,#genre#":[
"天津新闻频道","天津文艺频道","天津影视频道","天津都市频道","天津体育频道","天津教育频道","天津少儿频道","天津文旅频道","天视文旅频道","蓟州电视台","滨海1","滨海2"
    ],
    "新疆,#genre#":[
"新疆卫视2","新疆卫视3","新疆卫视4","新疆卫视5","新疆卫视6","新疆卫视7","新疆卫视8","新疆卫视9","新疆卫视10","新疆卫视11","新疆卫视12","包头TV1","包头TV2","包头TV3","乌鲁木齐1","阿克苏1","阿克苏2","阿拉尔","阿勒泰1","克孜勒苏柯尔克孜1","克孜勒苏柯尔克孜2","克孜勒苏柯尔克孜3","伊犁哈萨克1","伊犁哈萨克2","伊犁哈萨克3","伊犁哈萨克4","喀什1","喀什2","喀什3","巴音郭楞1","巴音郭楞2","巴音郭楞3","巴音郭楞4","昌吉市电视台","霍城1","呼图壁1","玛纳斯1","竹山1","竹山2","奎屯1","奎屯3","哈密TV1","哈密TV3"
    ],
    "云南,#genre#":[
"云南都市频道","云南娱乐频道","云南影视频道","云南康旅频道","云南少儿频道","澜湄国际频道","云南4K频道","楚雄新闻频道","禄丰市电视台"
    ]
}

# 简化的频道名称映射
CHANNEL_NAME_MAPPING = {
    "CCTV-1综合": ["CCTV-1", "CCTV-1HD", "CCTV1HD", "CCTV1"],
    "CCTV-2财经": ["CCTV-2", "CCTV-2HD", "CCTV2HD", "CCTV2"],
    "CCTV-3综艺": ["CCTV-3", "CCTV-3HD", "CCTV3HD", "CCTV3"],
    "CCTV-4中文国际": ["CCTV-4", "CCTV-4HD", "CCTV4HD", "CCTV4"],
    "CCTV-5体育": ["CCTV-5", "CCTV-5HD", "CCTV5HD", "CCTV5"],
    "CCTV-5+体育赛事": ["CCTV-5+", "CCTV-5+HD", "CCTV5+HD", "CCTV5+"],
    "CCTV-6电影": ["CCTV-6", "CCTV-6HD", "CCTV6HD", "CCTV6"],
    "CCTV-7国防军事": ["CCTV-7", "CCTV-7HD", "CCTV7HD", "CCTV7"],
    "CCTV-8电视剧": ["CCTV-8", "CCTV-8HD", "CCTV8HD", "CCTV8"],
    "CCTV-9纪录": ["CCTV-9", "CCTV-9HD", "CCTV9HD", "CCTV9"],
    "CCTV-10科教": ["CCTV-10", "CCTV-10HD", "CCTV10HD", "CCTV10"],
    "CCTV-11戏曲": ["CCTV-11", "CCTV-11HD", "CCTV11HD", "CCTV11"],
    "CCTV-12社会与法": ["CCTV-12", "CCTV-12HD", "CCTV12HD", "CCTV12"],
    "CCTV-13新闻": ["CCTV-13", "CCTV-13HD", "CCTV13HD", "CCTV13"],
    "CCTV-14少儿": ["CCTV-14", "CCTV-14HD", "CCTV14HD", "CCTV14"],
    "CCTV-15音乐": ["CCTV-15", "CCTV-15HD", "CCTV15HD", "CCTV15"],
    "CCTV-16奥林匹克": ["CCTV-16", "CCTV-16HD", "CCTV-164K", "CCTV16", "CCTV164K", "CCTV-16奥林匹克4K"],
    "CCTV-17农业农村": ["CCTV-17", "CCTV-17HD", "CCTV17HD", "CCTV17"],
    "CCTV-4欧洲":["CCTV4欧洲","CCTV-4欧洲","CCTV4欧洲HD","CCTV-4欧洲","CCTV-4中文国际欧洲","CCTV4中文欧洲"],
"CCTV-4美洲":["CCTV4美洲","CCTV-4北美","CCTV4美洲HD","CCTV-4美洲","CCTV-4中文国际美洲","CCTV4中文美洲"],
"CCTV-4K":["CCTV4K超高清","CCTV4K","CCTV-4K超高清","CCTV4K"],
"CCTV-8K":["CCTV8K超高清","CCTV8K","CCTV-8K超高清","CCTV8K"],
"兵器科技":["CCTV-兵器科技","CCTV兵器科技"],
"风云音乐":["CCTV-风云音乐","CCTV风云音乐"],
"第一剧场":["CCTV-第一剧场","CCTV第一剧场"],
"风云足球":["CCTV-风云足球","CCTV风云足球"],
"风云剧场":["CCTV-风云剧场","CCTV风云剧场"],
"怀旧剧场":["CCTV-怀旧剧场","CCTV怀旧剧场"],
"女性时尚":["CCTV-女性时尚","CCTV女性时尚"],
"世界地理":["CCTV-世界地理","CCTV世界地理"],
"央视台球":["CCTV-央视台球","CCTV央视台球"],
"高尔夫网球":["CCTV-高尔夫网球","CCTV高尔夫网球","CCTV央视高网","CCTV-高尔夫·网球","央视高网"],
"央视文化精品":["CCTV-央视文化精品","CCTV央视文化精品","CCTV文化精品","CCTV-文化精品","文化精品"],
"卫生健康":["CCTV-卫生健康","CCTV卫生健康"],
"电视指南":["CCTV-电视指南","CCTV电视指南"],
"农林卫视":["陕西农林卫视"],
"三沙卫视":["海南三沙卫视"],
"兵团卫视":["新疆兵团卫视"],
"延边卫视":["吉林延边卫视"],
"安多卫视":["青海安多卫视"],
"康巴卫视":["四川康巴卫视"],
"山东教育卫视":["山东教育","教育卫视"],
"中国教育1台":["CETV1","中国教育一台","中国教育1","CETV-1综合教育","CETV-1"],
"中国教育2台":["CETV2","中国教育二台","中国教育2","CETV-2空中课堂","CETV-2"],
"中国教育3台":["CETV3","中国教育三台","中国教育3","CETV-3教育服务","CETV-3"],
"中国教育4台":["CETV4","中国教育四台","中国教育4","CETV-4职业教育","CETV-4"],
"早期教育":["中国教育5台","中国教育5","中国教育五台","CETV早期教育","华电早期教育","CETV早期教育","CETV-5","CETV5"],
"湖南卫视4K":["湖南卫视4K"],
"北京卫视4K":["北京卫视4K"],
"东方卫视4K":["东方卫视4K"],
"广东卫视4K":["广东卫视4K"],
"深圳卫视4K":["深圳卫视4K"],
"山东卫视4K":["山东卫视4K"],
"四川卫视4K":["四川卫视4K"],
"浙江卫视4K":["浙江卫视4K"],
"CHC影迷电影":["CHC高清电影","CHC-影迷电影","影迷电影","chc高清电影"],
"北京IPTV淘电影":["IPTV淘电影","淘电影","北京淘电影"],
"北京IPTV淘精彩":["IPTV淘精彩","淘精彩","北京淘精彩"],
"北京IPTV淘剧场":["IPTV淘剧场","淘剧场","北京淘剧场"],
"北京IPTV4K超清":["IPTV淘4K","4K超清","北京淘4K","淘4K","淘4K"],
"北京IPTV淘娱乐":["IPTV淘娱乐","淘娱乐","北京淘娱乐"],
"北京IPTV淘BABY":["IPTV淘BABY","淘BABY","北京淘BABY","IPTV淘baby","北京IPTV淘baby","北京淘baby"],
"北京IPTV萌宠TV":["IPTV淘萌宠","萌宠TV","北京淘萌宠"],
"魅力足球":["上海魅力足球"],
"睛彩青少":["睛彩羽毛球"],
"求索纪录":["求索记录","求索纪录4K","求索记录4K","求索纪录4K","求索记录4K"],
"金鹰纪实":["湖南金鹰纪实","金鹰记实"],
"纪实科教":["北京纪实科教","BRTV纪实科教","纪实科教8K"],
"星空卫视":["星空衛視","星空衛视","星空卫視"],
"CHANNEL[V]":["CHANNEL-V","Channel[V]"],
"凤凰卫视":["凤凰中文","凤凰中文台","凤凰卫视中文","凤凰卫视"],
"凤凰资讯":["凤凰资讯","凤凰资讯台","凤凰咨询","凤凰咨询台","凤凰卫视咨询台","凤凰卫视资讯","凤凰卫视咨询"],
"凤凰香港":["凤凰香港台","凤凰卫视香港","凤凰香港"],
"凤凰电影":["凤凰电影","凤凰电影台","凤凰卫视电影","鳳凰衛視電影台","凤凰电影"],
"茶频道":["湖南茶频道"],
"快乐垂钓":["湖南快乐垂钓"],
"先锋乒羽":["湖南先锋乒羽"],
"天元围棋":["天元围棋频道"],
"汽摩":["重庆汽摩","汽摩频道","重庆汽摩频道"],
"梨园频道":["河南梨园频道","梨园","河南梨园"],
"文物宝库":["河南文物宝库"],
"武术世界":["河南武术世界"],
"乐游":["乐游频道","上海乐游频道","乐游纪实","SiTV乐游频道","SiTV乐游频道"],
"欢笑剧场":["上海欢笑剧场4K","欢笑剧场4K","欢笑剧场4K","上海欢笑剧场"],
"生活时尚":["生活时尚4K","SiTV生活时尚","上海生活时尚"],
"都市剧场":["都市剧场4K","SiTV都市剧场","上海都市剧场"],
"游戏风云":["游戏风云4K","SiTV游戏风云","上海游戏风云"],
"金色学堂":["金色学堂4K","SiTV金色学堂","上海金色学堂"],
"动漫秀场":["动漫秀场4K","SiTV动漫秀场","上海动漫秀场"],
"卡酷少儿":["北京KAKU少儿","BRTV卡酷少儿","北京卡酷少儿","卡酷动画"],
"哈哈炫动":["炫动卡通","上海哈哈炫动"],
"优漫卡通":["江苏优漫卡通","优漫漫画"],
"金鹰卡通":["湖南金鹰卡通"],
"中国交通":["中国交通频道"],
"中国天气":["中国天气频道"],
"华数4K":["华数低于4K","华数4K电影","华数爱上4K"],
"iHOT爱喜剧":["iHOT爱喜剧","IHOT爱喜剧","IHOT爱喜剧","ihot爱喜剧","爱喜剧","ihot爱喜剧"],
"iHOT爱科幻":["iHOT爱科幻","IHOT爱科幻","IHOT爱科幻","ihot爱科幻","爱科幻","ihot爱科幻"],
"iHOT爱院线":["iHOT爱院线","IHOT爱院线","IHOT爱院线","ihot爱院线","ihot爱院线","爱院线"],
"iHOT爱悬疑":["iHOT爱悬疑","IHOT爱悬疑","IHOT爱悬疑","ihot爱悬疑","ihot爱悬疑","爱悬疑"],
"iHOT爱历史":["iHOT爱历史","IHOT爱历史","IHOT爱历史","ihot爱历史","ihot爱历史","爱历史"],
"iHOT爱谍战":["iHOT爱谍战","IHOT爱谍战","IHOT爱谍战","ihot爱谍战","ihot爱谍战","爱谍战"],
"iHOT爱旅行":["iHOT爱旅行","IHOT爱旅行","IHOT爱旅行","ihot爱旅行","ihot爱旅行","爱旅行"],
"iHOT爱幼教":["iHOT爱幼教","IHOT爱幼教","IHOT爱幼教","ihot爱幼教","ihot爱幼教","爱幼教"],
"iHOT爱玩具":["iHOT爱玩具","IHOT爱玩具","IHOT爱玩具","ihot爱玩具","ihot爱玩具","爱玩具"],
"iHOT爱体育":["iHOT爱体育","IHOT爱体育","IHOT爱体育","ihot爱体育","ihot爱体育","爱体育"],
"iHOT爱赛车":["iHOT爱赛车","IHOT爱赛车","IHOT爱赛车","ihot爱赛车","ihot爱赛车","爱赛车"],
"iHOT爱浪漫":["iHOT爱浪漫","IHOT爱浪漫","IHOT爱浪漫","ihot爱浪漫","ihot爱浪漫","爱浪漫"],
"iHOT爱奇谈":["iHOT爱奇谈","IHOT爱奇谈","IHOT爱奇谈","ihot爱奇谈","ihot爱奇谈","爱奇谈"],
"iHOT爱科学":["iHOT爱科学","IHOT爱科学","IHOT爱科学","ihot爱科学","ihot爱科学","爱科学"],
"iHOT爱动漫":["iHOT爱动漫","IHOT爱动漫","IHOT爱动漫","ihot爱动漫","ihot爱动漫","爱动漫"],
# 更多映射规则...（需要补充完整）
}

def normalize_channel_name(channel_name):
    """标准化频道名称"""
    channel_name_clean = channel_name.strip()
    
    # 先精确匹配
    for standard_name, variants in CHANNEL_NAME_MAPPING.items():
        if channel_name_clean in variants:
            return standard_name
    
    # 然后模糊匹配
    for standard_name, variants in CHANNEL_NAME_MAPPING.items():
        for variant in variants:
            if variant.lower() in channel_name_clean.lower() or channel_name_clean.lower() in variant.lower():
                return standard_name
                
    return channel_name_clean

def categorize_channels(formatted_channels):
    """根据分类规则重新分类频道"""
    debug_log("开始分类频道...")
    categorized = defaultdict(list)
    uncategorized = []
    
    for channel_line in formatted_channels:
        # 解析频道行
        match = re.match(r'^"([^"]+)","([^"]+)"\$"([^"]+)"$', channel_line)
        if not match:
            continue
            
        channel_name, channel_url, region = match.groups()
        normalized_name = normalize_channel_name(channel_name)
        
        # 查找分类
        categorized_flag = False
        for category, channels in CATEGORY_MAPPING.items():
            if normalized_name in channels:
                categorized[category].append(f'"{normalized_name}","{channel_url}"')
                categorized_flag = True
                break
        
        if not categorized_flag:
            uncategorized.append(channel_line)
    
    debug_log(f"分类完成: 已分类 {sum(len(channels) for channels in categorized.values())}, 未分类 {len(uncategorized)}")
    return categorized, uncategorized

def generate_output_files(categorized_channels, uncategorized_channels, all_channels):
    """生成输出文件"""
    debug_log("开始生成输出文件...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # 生成重新分类的文件
        with open('reclassified_live_sources.txt', 'w', encoding='utf-8') as f:
            f.write(f"# 直播源重新分类结果\n")
            f.write(f"# 生成时间: {timestamp}\n")
            f.write(f"# 数据来源: https://github.com/q1017673817/iptvz/blob/main/zubo_all.txt\n\n")
            
            for category in sorted(categorized_channels.keys()):
                if categorized_channels[category]:
                    f.write(f"{category}\n")
                    for channel in categorized_channels[category]:
                        f.write(f"{channel}\n")
                    f.write("\n")
            
            # 添加未分类的频道
            if uncategorized_channels:
                f.write('其他,#genre#\n')
                for channel in uncategorized_channels:
                    f.write(f"{channel}\n")
        
        debug_log("reclassified_live_sources.txt 生成成功")
        
        # 生成格式化的原始文件（不分类）
        with open('formatted_live_sources.txt', 'w', encoding='utf-8') as f:
            f.write(f"# 格式化直播源（未分类）\n")
            f.write(f"# 生成时间: {timestamp}\n")
            f.write(f"# 数据来源: https://github.com/q1017673817/iptvz/blob/main/zubo_all.txt\n\n")
            for channel_line in all_channels:
                f.write(f"{channel_line}\n")
        
        debug_log("formatted_live_sources.txt 生成成功")
        
    except Exception as e:
        debug_log(f"生成文件失败: {e}")
        raise

def main():
    """主函数"""
    try:
        debug_log("脚本开始执行")
        
        github_url = "https://github.com/q1017673817/iptvz/blob/main/zubo_all.txt"
        
        debug_log("正在获取原始数据...")
        original_content = fetch_original_data(github_url)
        if not original_content:
            debug_log("无法获取数据，程序退出")
            return 1
        
        # 保存原始数据用于调试
        with open('debug_original_content.txt', 'w', encoding='utf-8') as f:
            f.write(original_content)
        debug_log("原始数据已保存到 debug_original_content.txt")
        
        # 显示前5行用于调试
        lines = original_content.split('\n')
        debug_log("原始数据前5行:")
        for i, line in enumerate(lines[:5]):
            debug_log(f"行 {i+1}: {line}")
        
        debug_log("正在解析和格式化数据（跳过前两行）...")
        formatted_channels = parse_original_data_skip_first_two_lines(original_content)
        debug_log(f"成功解析 {len(formatted_channels)} 个频道")
        
        if len(formatted_channels) == 0:
            debug_log("错误: 仍然没有解析到任何频道")
            return 1
        
        debug_log("正在重新分类频道...")
        categorized_channels, uncategorized_channels = categorize_channels(formatted_channels)
        
        debug_log("正在生成输出文件...")
        generate_output_files(categorized_channels, uncategorized_channels, formatted_channels)
        
        debug_log("完成！")
        debug_log(f"已处理频道总数: {len(formatted_channels)}")
        debug_log(f"已分类频道数: {sum(len(channels) for channels in categorized_channels.values())}")
        debug_log(f"未分类频道数: {len(uncategorized_channels)}")
        debug_log("生成的文件:")
        debug_log("- reclassified_live_sources.txt (重新分类的直播源)")
        debug_log("- formatted_live_sources.txt (仅格式化的直播源)")
        
        return 0
        
    except Exception as e:
        debug_log(f"脚本执行过程中发生错误: {e}")
        debug_log("详细错误信息:")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
