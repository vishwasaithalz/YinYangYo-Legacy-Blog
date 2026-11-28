#!/usr/bin/env python3
"""Patch an exported CURRENT Blogger XML theme. Never submit live writes.

Usage: python blogger_layout_repair.py current-backup.xml repaired-theme.xml
       python blogger_layout_repair.py --self-test
Requires lxml. Refuses rendered HTML and refuses to overwrite output.
"""
from pathlib import Path
import sys
from lxml import etree

B = 'http://www.google.com/2005/gml/b'
H = 'http://www.w3.org/1999/xhtml'
TOPICS = [('Windows & PC', '/search/label/PC%20HACKS'),
          ('Android', '/search/label/ANDROID'),
          ('Security', '/search/label/CYBERSECURITY'),
          ('Tips & Internet', '/search/label/TIPS%20N%20TRICKS')]
NAV = [('Home', '/'), ('Legacy Posts', '/#yyh-legacy-archive')] + TOPICS
CSS = '''
/* YYH accessible layout repair 2026-11-27 */
.cf-container{width:calc(100% - 32px);max-width:1280px;margin-inline:auto;min-width:0}
.cf-header .cf-nav-inner{display:flex;flex-wrap:wrap;gap:12px;align-items:center;min-width:0}
.cf-header .cf-nav-links{display:flex!important;flex:1 1 100%;flex-wrap:wrap;gap:6px;min-width:0}
.cf-header .cf-nav-link{white-space:normal;min-height:44px;display:inline-flex;align-items:center;padding:8px 12px}
.cf-hero-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(180px,260px);gap:24px;align-items:center}
.cf-hero-main,.cf-hud-metrics{min-width:0;max-width:100%}
.cf-hero-h1{font-size:clamp(28px,4vw,46px);line-height:1.15;overflow-wrap:anywhere}
.cf-articles-grid,.yyh-feed-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;align-items:stretch}
.cf-card,.yyh-feed-card,.cf-post-body{min-width:0;overflow-wrap:anywhere}
.cf-post-body{max-width:78ch;margin-inline:auto;line-height:1.8}
.cf-post-body img{max-width:100%;height:auto}
.cf-post-body pre{max-width:100%;overflow-x:auto;white-space:pre}
.cf-post-body table{display:block;max-width:100%;overflow-x:auto}
.cf-filter-pills{display:flex;flex-wrap:wrap;gap:8px}
a:focus-visible,button:focus-visible{outline:3px solid #ffd21a;outline-offset:4px}
@media(max-width:900px){.cf-articles-grid,.yyh-feed-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.cf-hero-grid{grid-template-columns:minmax(0,1fr)}}
@media(max-width:600px){.cf-container{width:calc(100% - 24px)}.cf-articles-grid,.yyh-feed-grid{grid-template-columns:minmax(0,1fr)}.cf-brand{min-width:0}.cf-brand-title{font-size:clamp(15px,4.7vw,20px)}.cf-telemetry-bar{flex-wrap:wrap;gap:8px}.cf-telemetry-left,.cf-telemetry-right{min-width:0;flex-wrap:wrap}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation:none!important;transition:none!important}}
'''

def has_class(root, name):
    return root.xpath('//*[contains(concat(" ",normalize-space(@class)," "),$token)]', token=' '+name+' ')

def replace_links(node, links, class_name=None):
    for child in list(node):
        node.remove(child)
    node.text = None
    for title, href in links:
        a = etree.SubElement(node, '{'+H+'}a', href=href)
        if class_name:
            a.set('class', class_name)
        a.text = title

def patch(source):
    parser = etree.XMLParser(resolve_entities=False, no_network=True, strip_cdata=False)
    root = etree.fromstring(source, parser)
    skins = root.findall('.//{'+B+'}skin')
    if len(skins) != 1:
        raise ValueError('Use the current Blogger XML backup, not rendered page HTML.')
    if 'YYH accessible layout repair 2026-11-27' in (skins[0].text or ''):
        raise ValueError('Repair already present; start from the original backup.')
    nav = has_class(root, 'cf-nav-links')
    drawers = has_class(root, 'cf-mobile-drawer')
    if len(nav) != 1 or len(drawers) != 1:
        raise ValueError('Live-theme selectors changed; inspect before applying.')
    # No widgets, article data expressions, archive links, or post bodies touched.
    replace_links(nav[0], NAV, 'cf-nav-link')
    replace_links(drawers[0], NAV)
    for node in has_class(root, 'cf-filter-pills'):
        replace_links(node, [('All Articles', '/')]+TOPICS, 'cf-pill')
    for node in has_class(root, 'cf-hero-h1'):
        for child in list(node): node.remove(child)
        node.text = 'Computers, curiosity and the original internet archive'
    for node in has_class(root, 'cf-hero-desc'):
        node.text = 'Explore 25 preserved articles on Android, Windows, security learning and internet culture. Original URLs, with history kept in view.'
    skins[0].text = etree.CDATA((skins[0].text or '')+'\n'+CSS)
    return etree.tostring(root, encoding='UTF-8', xml_declaration=True)

def self_test():
    import unittest
    fixture = f'''<html xmlns="{H}" xmlns:b="{B}"><head><b:skin><![CDATA[body{{color:green}}]]></b:skin></head><body><nav class="cf-nav-links"><a href="/old">Old</a></nav><div class="cf-mobile-drawer"/><div class="cf-filter-pills"/><h1 class="cf-hero-h1">Old <span>heading</span></h1><p class="cf-hero-desc">old</p><section id="yyh-legacy-archive"><a href="/2013/original.html">Original</a></section><b:widget id="Blog1" type="Blog"/></body></html>'''.encode()
    class Tests(unittest.TestCase):
        def test_navigation_and_original_archive(self):
            r=etree.fromstring(patch(fixture))
            self.assertEqual([(x.text,x.get('href')) for x in has_class(r,'cf-nav-links')[0]],NAV)
            self.assertEqual([(x.text,x.get('href')) for x in has_class(r,'cf-mobile-drawer')[0]],NAV)
            self.assertEqual(r.xpath('//*[@id="yyh-legacy-archive"]/*')[0].get('href'),'/2013/original.html')
            self.assertEqual(r.find('.//{'+B+'}widget').get('id'),'Blog1')
        def test_repeat_rejected(self):
            with self.assertRaises(ValueError): patch(patch(fixture))
        def test_rendered_html_rejected(self):
            with self.assertRaises(ValueError): patch(b'<html><head/></html>')
        def test_changed_selectors_rejected(self):
            with self.assertRaises(ValueError): patch(fixture.replace(b'cf-nav-links',b'other-nav'))
        def test_original_style_retained(self):
            self.assertIn(b'body{color:green}',patch(fixture))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        raise SystemExit(self_test())
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    source, destination = map(Path,sys.argv[1:])
    repaired = patch(source.read_bytes())
    with destination.open('xb') as f: f.write(repaired)
    print(f'Created {destination}. Not uploaded to Blogger. Keep the source as rollback.')
