import asyncio
import aiohttp
from bs4 import BeautifulSoup
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class Node:
    def __init__(self, url, head=None, deep=None):
        if deep:
            self.deep = deep
        self.url = url
        self.nodes = []
        if head is None:
            self.head = self
            self.paths = {url: self}
        else:
            self.head = head
            head.paths[url] = self
            self.paths = head.paths

    def __contains__(self, item):
        return item in self.paths

    def __str__(self):
        return f"{self.url}: deep={self.head.deep}, first_nodes={len(self.nodes)}, power={len(self.paths)}"

    def __getitem__(self, item):
        return self.paths[item]

async def parse_site(link, ses):
    try:
        resp = await ses.get(link, timeout=5)
        resp = await resp.read()
        return set(_['href'] for _ in BeautifulSoup(resp.decode('utf-8'), 'html.parser').find_all('a', href=True) if len(_['href']) > 2)
    except:
        return []

async def get_branch(url, node=None, deep=2, ses=None):
    if node is None:
        node = Node(url, deep=deep)
        start_time = datetime.utcnow()
    else:
        if url[:4] != 'http':
            sep = ''
            if '/' not in [node.url[-1], url[0]]:
                sep = '/'
            url = node.url + sep + url
        if url in node:
            node.nodes.append(node[url])
            return
        new = Node(url, head=node.head)
        node.nodes.append(new)
        node = new

    if not deep:
        return node

    links = await parse_site(url, ses)
    await asyncio.gather(*[get_branch(_, node=node, deep=deep-1, ses=ses) for _ in links])

    if node.head == node:
        print(f"{node} | {datetime.utcnow()-start_time}")
    return node

async def get_sites_map(links):
    async with aiohttp.ClientSession() as ses:
        tasks = []
        for _ in links:
            if not isinstance(_, str):
                url, deep = _
                tasks.append(get_branch(url, deep=deep, ses=ses))
                continue
            tasks.append(get_branch(_, ses=ses))
        branches = await asyncio.gather(*tasks)
        return {_.url: _ for _ in branches}

def save_graph(node, graph=None, paths=None, deep=0):
    if graph is None:
        graph = nx.DiGraph()
        paths = []
    if node.url in paths:
        return

    graph.add_node(node.url, c=['r', 'b', 'g', 'y', 'pink'][min(deep, 4)])
    paths.append(node.url)

    for _ in node.nodes:
        graph.add_edge(node.url, _.url)
        save_graph(_, graph=graph, paths=paths, deep=deep+1)

    if node.head != node:
        return

    nx.draw(graph, nx.kamada_kawai_layout(graph), node_color=nx.get_node_attributes(graph, 'c').values(), alpha=0.3)
    plt.savefig(f"pics/{node.url.split('//')[1]}_{node.deep}.png")
    plt.close()

if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    urls = [
        ('http://crawler-test.com', 1),
        'http://google.com',
        'https://vk.com',
        'https://yandex.ru',
        ('https://stackoverflow.com', 1),
    ]

    sites = asyncio.run(get_sites_map(urls))
    for _ in sites:
        save_graph(sites[_])
