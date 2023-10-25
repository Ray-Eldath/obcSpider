import requests
from lxml import etree

VoiceLines = list[tuple[str, str, str]]


def initial(x):
    assert len(x) == 1
    return x[0]


def select(doc, val: str, sub: str = 'list') -> any:
    return initial([e[sub] for e in doc if e['name'] == val])


def lift(x, f=lambda id: id):
    assert len(x) <= 1
    return f(x[0]) if len(x) == 1 else None


def extract_lang_id(doc, lang_id: int) -> int:
    languages = ['汉语', '日语', '韩语', '英语']
    return initial(doc.xpath(f'//ul[@data-target="voiceTab.attr"][1]/li[text()="{languages[lang_id]}"]/@data-index'))


def extract_voice_lines(doc, lang_idx: int) -> VoiceLines:
    tbody_xpath = f'//li[@data-index="{lang_idx}"]/table[@class="obc-tmpl-character__voice-pc"]/tbody'
    voice_xpath = f'{tbody_xpath}/tr/td/div'
    titles = [s.strip() for s in doc.xpath(f'{tbody_xpath}/tr/td[@class="h3"]/text()')]
    voices = doc.xpath(voice_xpath)
    lines = [lift(e.xpath('./span/text()'), lambda str: str.strip()) for e in voices]
    audios = [lift(e.xpath('./div/audio/source/@src')) for e in voices]
    assert len(titles) == len(lines) == len(audios)
    return list(zip(titles, lines, audios))


class ObcSpider:
    def __init__(self, include: list[str] = None,
                 exclude: list[str] = None,
                 lang_id: int = 0):
        home_url = 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/home/content/list?app_sn=ys_obc&channel_id=189'
        # home_url = 'https://api-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list?app_sn=sr_wiki&channel_id=17'
        home = requests.get(home_url).json()['data']['list']
        handbook = select(home, '图鉴', sub='children')
        # handbook = select(home, '游戏图鉴', sub='children')
        character = select(handbook, '角色')
        print([(e['title'], e['content_id']) for e in character])
        content_ids = [e['content_id'] for e in character if
                       (include is None or e['title'] in include) and (exclude is None or e['title'] not in exclude)]
        assert include is None or len(content_ids) == len(include)
        self.content_ids = content_ids
        self.lang_id = lang_id
        self.idx = 0

    def next(self):
        cid = self.content_ids[self.idx]
        detail_url = f"https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/content/info?app_sn=ys_obc&content_id={cid}"
        # detail_url = f"https://api-static.mihoyo.com/common/blackboard/sr_wiki/v1/content/info?app_sn=sr_wiki&content_id={cid}"
        detail_payload = requests.get(detail_url).json()
        if detail_payload['retcode'] < 0:
            return None
        detail = detail_payload['data']['content']
        html = etree.HTML(select(detail['contents'], '角色展示', sub='text'))
        # html = etree.HTML(detail['contents'][0]['text'])
        lang_idx = extract_lang_id(html, lang_id)
        return detail['title'], detail['summary'], cid, extract_voice_lines(html, lang_idx)

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if self.idx >= len(self.content_ids):
                raise StopIteration
            val = self.next()
            self.idx += 1
            if val is not None:
                return val


if __name__ == '__main__':
    lang_id = 0
    for (name, summary, cid, lines) in ObcSpider(exclude=['迪希雅', '班尼特', '莱欧斯利', '那维莱特'], lang_id=lang_id):
        print(f"{name} - {summary}")
        for (title, line, audio_url) in lines:
            print(f"\t{title} - {line}: {audio_url}")
