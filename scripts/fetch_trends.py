#!/usr/bin/env python3
"""
多平台热点抓取脚本
支持：微博、知乎、抖音、B站、百度
"""

import json
import re
import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# 关键词配置（你的账号定位：科技+生活）
KEYWORDS = {
    'include': [
        'AI', '人工智能', 'ChatGPT', '大模型', 'AIGC', '数字人', '自动驾驶', '机器人',
        '科技', '技术', '数码', '软件', 'App', '互联网', '创业', '商业', '职场',
        '评测', '测评', '教程', '盘点', '揭秘', '真相', '逆天', '离谱'
    ],
    'exclude': [
        '色情', '赌博', '诈骗', '暴力', '政治'
    ]
}

def filter_by_keywords(title):
    """根据关键词过滤"""
    title_lower = title.lower()
    
    # 排除敏感词
    for word in KEYWORDS['exclude']:
        if word in title:
            return False
            
    # 必须包含至少一个关键词
    for word in KEYWORDS['include']:
        if word.lower() in title_lower:
            return True
    return False

def fetch_weibo():
    """抓取微博热搜"""
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        results = []
        for item in data.get('data', {}).get('realtime', [])[:20]:
            title = item.get('word', '')
            if title:
                results.append({
                    'platform': '微博',
                    'title': title,
                    'url': f'https://s.weibo.com/weibo?q={title}'
                })
        return results
    except Exception as e:
        print(f"微博抓取失败: {e}")
        return []

def fetch_zhihu():
    """抓取知乎热榜"""
    try:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20"
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        data = resp.json()
        results = []
        for item in data.get('data', [])[:20]:
            title = item.get('target', {}).get('title', '')
            if title:
                url = item.get('target', {}).get('url', '')
                results.append({
                    'platform': '知乎',
                    'title': title,
                    'url': f'https://www.zhihu.com{url}'
                })
        return results
    except Exception as e:
        print(f"知乎抓取失败: {e}")
        return []

def fetch_bilibili():
    """抓取B站热榜"""
    try:
        url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        results = []
        for item in data.get('data', {}).get('list', [])[:20]:
            results.append({
                'platform': 'B站',
                'title': item.get('title', ''),
                'url': f'https://www.bilibili.com/video/{item.get("bvid", "")}'
            })
        return results
    except Exception as e:
        print(f"B站抓取失败: {e}")
        return []

def fetch_baidu():
    """抓取百度热搜"""
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(resp.text, 'lxml')
        results = []
        for item in soup.select('.item-wrap')[:20]:
            title = item.select_one('.title')
            if title:
                results.append({
                    'platform': '百度',
                    'title': title.get_text(strip=True),
                    'url': 'https://top.baidu.com' + item.get('href', '')
                })
        return results
    except Exception as e:
        print(f"百度抓取失败: {e}")
        return []

def main():
    print("=" * 50)
    print("🔥 热点抓取开始")
    print("=" * 50)
    
    all_trends = []
    
    # 抓取各平台
    print("\n📱 抓取微博...")
    all_trends.extend(fetch_weibo())
    
    print("📱 抓取知乎...")
    all_trends.extend(fetch_zhihu())
    
    print("📱 抓取B站...")
    all_trends.extend(fetch_bilibili())
    
    print("📱 抓取百度...")
    all_trends.extend(fetch_baidu())
    
    # 关键词过滤
    print(f"\n🔍 关键词过滤 ({len(all_trends)} 条 → ", end='')
    filtered = [t for t in all_trends if filter_by_keywords(t['title'])]
    print(f"{len(filtered)} 条)")
    
    # 去重
    seen = set()
    unique = []
    for t in filtered:
        key = t['title']
        if key not in seen:
            seen.add(key)
            unique.append(t)
    
    # 按平台分组输出
    print(f"\n✅ 去重后 {len(unique)} 条热点:")
    platforms = {}
    for t in unique:
        p = t['platform']
        if p not in platforms:
            platforms[p] = []
        platforms[p].append(t['title'])
    
    for p, titles in platforms.items():
        print(f"\n{p}:")
        for i, t in enumerate(titles[:5], 1):
            print(f"  {i}. {t}")
    
    # 保存到文件
    output = {
        'updated': datetime.now().isoformat(),
        'trends': unique[:30]  # 最多30条
    }
    
    with open('trends.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 已保存到 trends.json")
    
    # 推送到飞书（如果配置了 webhook）
    webhook = os.environ.get('FEISHU_WEBHOOK')
    if webhook and unique:
        send_feishu(webhook, unique[:5])
    
    return output

def send_feishu(webhook, trends):
    """推送到飞书"""
    text = "🔥 **热点更新**\n\n"
    for i, t in enumerate(trends, 1):
        text += f"{i}. {t['title']} ({t['platform']})\n"
    
    try:
        requests.post(webhook, json={'msg_type': 'text', 'content': {'text': text}}, timeout=5)
        print("📤 已推送到飞书")
    except Exception as e:
        print(f"飞书推送失败: {e}")

if __name__ == '__main__':
    main()