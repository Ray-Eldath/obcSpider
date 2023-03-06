import requests
from lxml import etree
import sqlite3

VoiceLines = list[tuple[str, str, str]]


def lift(x):
    assert len(x) == 1
    return x[0]


def select(doc, val: str, sub: str = 'list') -> any:
    return lift([e[sub] for e in doc if e['name'] == val])


def extract_lang_id(doc, lang_id: int) -> int:
    languages = ['汉语', '日语', '韩语', '英语']
    return lift(doc.xpath(f'//ul[@data-target="voiceTab.attr"][1]/li[text()="{languages[lang_id]}"]/@data-index'))


def extract_voice_lines(doc, lang_idx: int) -> VoiceLines:
    tbody_xpath = f'//li[@data-index="{lang_idx}"]/table[@class="obc-tmpl-character__voice-pc"]/tbody'
    voice_xpath = f'{tbody_xpath}/tr/td/div[@class="obc-tmpl-character__voice-item obc-tmpl-character__play-voice"]'
    titles: list[str] = doc.xpath(f'{tbody_xpath}/tr/td[@class="h3"]/text()')
    lines: list[str] = [e.strip() for e in doc.xpath(f'{voice_xpath}/span/text()')]
    audios: list[str] = doc.xpath(f'{voice_xpath}/div/audio/source/@src')
    assert len(titles) == len(lines) == len(audios)
    return list(zip(titles, lines, audios))


class ObcSpider:
    def __init__(self, targets: list[str] = None,
                 exclude: list[str] = None,
                 lang_id: int = 0):
        home_url = 'https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/home/content/list?app_sn=ys_obc&channel_id=189'
        home = requests.get(home_url).json()['data']['list']
        handbook = select(home, '图鉴', sub='children')
        character = select(handbook, '角色')
        print([e['title'] for e in character])
        content_ids = [e['content_id'] for e in character if
                       (targets is None or e['title'] in targets) and (exclude is None or e['title'] not in exclude)]
        assert targets is None or len(content_ids) == len(targets)
        self.content_ids = content_ids
        self.lang_id = lang_id
        self.idx = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.idx >= len(self.content_ids):
            raise StopIteration
        cid = self.content_ids[self.idx]
        detail_url = f"https://api-static.mihoyo.com/common/blackboard/ys_obc/v1/content/info?app_sn=ys_obc&content_id={cid}"
        detail = requests.get(detail_url).json()['data']['content']
        html = etree.HTML(select(detail['contents'], '角色展示', sub='text'))
        lang_idx = extract_lang_id(html, lang_id)
        self.idx += 1
        return detail['title'], detail['summary'], cid, extract_voice_lines(html, lang_idx)


if __name__ == '__main__':
    conn = sqlite3.connect('obcLines.db')
    lang_id = 3
    for (name, summary, cid, lines) in ObcSpider(exclude=['迪希雅', '班尼特'], lang_id=lang_id):
        conn.execute('INSERT INTO characters VALUES (?, ?, ?)', (name, summary, cid))
        print(f'{name} - {summary}')
        for line in lines:
            conn.execute('INSERT INTO lines VALUES (?, ?, ?, ?, ?)', (name, lang_id, line[0], line[1], line[2]))
        conn.commit()
    conn.close()
