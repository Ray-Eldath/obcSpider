import requests
from lxml import etree


def lift(x):
    assert len(x) == 1
    return x[0]


def select(doc, val: str, sub: str = 'list') -> any:
    return lift([e[sub] for e in doc if e['name'] == val])


def extract_lang_id(doc, lang_id: int) -> int:
    languages = ['汉语', '日语', '韩语', '英语']
    return lift(doc.xpath(f'//ul[@data-target="voiceTab.attr"][1]/li[text()="{languages[lang_id]}"]/@data-index'))


VoiceLines = list[tuple[str, str, str]]


def extract_voice_lines(doc, lang_idx: int) -> VoiceLines:
    tbody_xpath = f'//li[@data-index="{lang_idx}"]/table[@class="obc-tmpl-character__voice-pc"]/tbody'
    voice_xpath = f'{tbody_xpath}/tr/td/div[@class="obc-tmpl-character__voice-item obc-tmpl-character__play-voice"]'
    titles: list[str] = doc.xpath(f'{tbody_xpath}/tr/td[@class="h3"]/text()')
    lines: list[str] = [e.strip() for e in doc.xpath(f'{voice_xpath}/span/text()')]
    audios: list[str] = doc.xpath(f'{voice_xpath}/div/audio/source/@src')
    assert len(titles) == len(lines) == len(audios)
    return list(zip(titles, lines, audios))


def extract_characters_lines(targets: list[str], lang_id: int = 0) -> list[tuple[str, str, VoiceLines]]:
    """
    :param targets: 角色名，例如 ['枫原万叶', '阿贝多', '魈']。请确保传入的角色名正确无误。
    :param lang_id: 语言，0 汉语, 1 日语, 2 韩语, 3 英语
    :return:
        一个包含角色名、角色简介和角色语音的 list of tuples。
        格式：[
                ('角色名', '角色简介', [('语音名称', '语音字幕', '语音文件URL'), ...]),
                ('阿贝多', '西风骑士团首席炼金术士兼调查小队队长，被称做「白垩之子」的天才。',
                    [
                        ('想要了解阿贝多·其一', '有问题想问我？请说吧。啊，冒昧地问一句，应该不会花费太长时间吧？手头的研究马上要进入最后一个阶段了。', 'https://...'),
                        ('阿贝多的烦恼…', '时间真是不够用啊，即使把大部分麻烦的事情都推掉还是会觉得时间不够。', 'https://...'),
                        ('晚安…', '晚安，你先去休息吧，我打算把最后一个实验做完。既然你那么感兴趣…明日再会时，我再与你一起探讨实验结果吧。' ,'https://...'),
                        ...
                    ]),
                ('魈', '守护璃月的仙人，「夜叉」。美号「降魔大圣」，妙称「护法夜叉大将」。喜欢吃杏仁豆腐。', [...]),
            ]
    """
    home_url = 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/home/content/list?app_sn=ys_obc&channel_id=189'
    home = requests.get(home_url).json()['data']['list']
    handbook = select(home, '图鉴', sub='children')
    character = select(handbook, '角色')
    content_ids = [e['content_id'] for e in character if e['title'] in targets]
    assert len(content_ids) == len(targets)
    characters = []
    for cid in content_ids:
        detail_url = f"https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/content/info?app_sn=ys_obc&content_id={cid}"
        detail = requests.get(detail_url).json()['data']['content']
        html = etree.HTML(select(detail['contents'], '角色展示', sub='text'))
        idx = extract_lang_id(html, lang_id)
        characters.append((detail['title'], detail['summary'], extract_voice_lines(html, idx)))
    return characters


if __name__ == '__main__':
    for (name, summary, lines) in extract_characters_lines(['枫原万叶', '阿贝多', '魈']):
        print(f'{name} - {summary}')
        for line in lines:
            print(f'    {line[0]}: {"".join(line[1].splitlines())} {line[2]}')
