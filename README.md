# obcSpider

米游社语音爬虫，可自动爬取原神和星穹铁道角色的语音文本、wav链接等信息。支持多语言。

## 使用

`class ObcSpider` 是一个可枚举对象。可以直接使用`for`循环遍历：

```python
for (name, summary, cid, lines) in ObcSpider(configuration_key='honkai:_star_rail', lang_id=0, include=['彦卿']):
    print(f"{name} - {summary}")
    for (title, line, audio_url) in lines:
        print(f"\t{title} - {line}: {audio_url}")
```

- `configuration_key`，必填，表示获取哪个游戏。只有 `honkai:_star_rail` 和 `genshin_impact` 两个选择。默认为 `genshin_impact`。
- `lang_id`：语言编号，从0到3分别为 `['汉语', '日语', '韩语', '英语']`。
- `exclude`：排除的角色名。
- `include`：包含的角色名。和 `exclude` 同时指定时，该项优先级更高。即结果中将首先包含 `include` 有的项，然后再去掉 `exclude` 排除的项。

---

除此以外，也可以直接执行 `obcSpider.py` 脚本，它会以人类可读的方式直接输出所有找到的角色名、角色简介、语音台词和语音wav地址。