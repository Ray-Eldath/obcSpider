from typing import Literal

import requests
from lxml import etree

Configurations = {
    'genshin_impact': {
        'home_url': 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/home/content/list?app_sn=ys_obc&channel_id=189',
        'detail_url': 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/content/info?app_sn=ys_obc&content_id={}',
        'language_tabs': ['汉语', '日语', '韩语', '英语'],
        'character_fn': lambda home: select(select(home, "图鉴", "children"), '角色'),
        'root_html_fn': lambda contents: select(contents, '角色展示', sub='text'),
    },
    'honkai:_star_rail': {
        'home_url': 'https://api-static.mihoyo.com/common/blackboard/sr_wiki/v1/home/content/list?app_sn=sr_wiki&channel_id=17',
        'detail_url': 'https://api-static.mihoyo.com/common/blackboard/sr_wiki/v1/content/info?app_sn=sr_wiki&content_id={}',
        'language_tabs': ['中', '日', '英', '韩'],
        'character_fn': lambda home: select(select(home, "游戏图鉴", "children"), '角色'),
        'root_html_fn': lambda contents: select(contents, '角色百科', sub='text'),
    }
}

VoiceLines = list[tuple[str, str, str]]


def initial(x):
    # assert len(x) == 1
    return x[0]


def select(doc, val: str, sub: str = 'list') -> any:
    return initial([e[sub] for e in doc if e['name'] == val])


def lift(x, f=lambda id: id):
    assert len(x) <= 1
    return f(x[0]) if len(x) == 1 else None


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
    def __init__(self, configuration_key: Literal['genshin_impact', 'honkai:_star_rail'] = 'genshin_impact',
                 include: list[str] = None,
                 exclude: list[str] = None,
                 lang_id: int = 0):
        self.configuration = Configurations[configuration_key]
        home_url = self.configuration['home_url']
        home = requests.get(home_url).json()['data']['list']
        character = self.configuration['character_fn'](home)
        print([(e['title'], e['content_id']) for e in character])
        content_ids = [e['content_id'] for e in character if
                       (include is None or e['title'] in include) and (exclude is None or e['title'] not in exclude)]
        assert include is None or len(content_ids) == len(include)
        self.content_ids = content_ids
        self.lang_id = lang_id
        self.idx = 0

    def next(self):
        cid = self.content_ids[self.idx]
        detail_url = self.configuration['detail_url'].format(cid)
        detail_payload = requests.get(detail_url).json()
        if detail_payload['retcode'] < 0:
            return None
        detail = detail_payload['data']['content']
        try:
            root = self.configuration['root_html_fn'](detail['contents'])
        except IndexError:
            return detail['title'], detail['summary'], cid, []
        root_html = etree.HTML(root)
        lang_idx = self.__extract_lang_id(root_html, lang_id)
        return detail['title'], detail['summary'], cid, extract_voice_lines(root_html, lang_idx)

    def __extract_lang_id(self, doc, lang_id: int) -> int:
        languages = self.configuration['language_tabs']
        return initial(doc.xpath(f'//ul[@data-target="voiceTab.attr"][1]/li[text()[contains(., "{languages[lang_id]}")]]/@data-index'))

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
    for (name, summary, cid, lines) in ObcSpider(configuration_key='honkai:_star_rail', lang_id=lang_id, include=['彦卿']):
        print(f"{name} - {summary}")
        for (title, line, audio_url) in lines:
            print(f"\t{title} - {line}: {audio_url}")
