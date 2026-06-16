"""
Teste automate pentru website-ul https://www.ocnadefier.ro
Autor: generat pentru rulare in PyCharm cu pytest.

Ce acopera:
- disponibilitatea paginilor principale
- continut minim asteptat pe pagini
- verificarea linkurilor interne si externe
- verificarea imaginilor si fisierelor statice
- verificari SEO de baza: title, meta description, heading-uri
- verificari contact: adresa, telefon, email, program
- verificari Monitorul Oficial Local / avizier electronic
- verificari formular cautare fara a trimite date reale
- testare browser cu Selenium: incarcare, navigare, responsive

Instalare dependinte:
    python -m pip install pytest requests beautifulsoup4 selenium webdriver-manager pytest-html

Rulare simpla:
    python -m pytest -v test_ocna_de_fier.py

Rulare cu raport HTML:
    python -m pytest -v test_ocna_de_fier.py --html=raport_ocna_de_fier.html --self-contained-html
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse, urldefrag

import pytest
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ocnadefier.ro"
TIMEOUT = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36 PytestWebsiteAudit/1.0"
    )
}

# Pagini publice identificate in meniul site-ului.
# Unele site-uri ale institutiilor publice pot avea slug-uri mai vechi sau redirect-uri.
MAIN_PAGES = [
    ("Acasa", "/"),
    ("Istoric", "/istoric"),
    ("Cultura", "/cultura"),
    ("Geografie", "/geografie"),
    ("Obiective turistice", "/obiective-turistice"),
    ("Lacase de cult", "/lacase-de-cult"),
    ("Obiceiuri si traditii", "/obiceiuri-si-traditii"),
    ("Ocupatii si mestesuguri", "/ocupatii-si-mestesuguri"),
    ("Evenimente locale", "/evenimente-locale"),
    ("Foto", "/foto"),
    ("Administratie locala", "/administratie-locala"),
    ("Contact", "/contact"),
    ("Monitorul Oficial Local", "/monitorul-oficial-local"),
]

EXPECTED_SITE_TEXT = [
    "COMUNA OCNA DE FIER",
    "Județul Caraș-Severin",
]

EXPECTED_CONTACT_TEXT = [
    "Primaria Comunei Ocna de Fier",
    "Str. Vale",
    "327190",
    "Caraș-Severin",
    "primaria@ocnadefier.ro",
]

ALLOWED_BROKEN_EXTERNAL_DOMAINS = {
    # Se poate completa aici daca exista servicii externe care blocheaza botii.
}


@dataclass(frozen=True)
class PageResponse:
    name: str
    path: str
    url: str
    response: requests.Response
    soup: BeautifulSoup


@pytest.fixture(scope="session")
def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def make_url(path: str) -> str:
    return urljoin(BASE_URL, path)


def get_page(session: requests.Session, path: str, *, allow_redirects: bool = True) -> requests.Response:
    return session.get(make_url(path), timeout=TIMEOUT, allow_redirects=allow_redirects)


def parse_html(response: requests.Response) -> BeautifulSoup:
    return BeautifulSoup(response.text, "html.parser")


def normalize_url(url: str) -> str:
    url, _fragment = urldefrag(url)
    return url.rstrip("/") or url


def is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"}


def is_internal_url(url: str) -> bool:
    parsed = urlparse(url)
    base = urlparse(BASE_URL)
    return parsed.netloc in {"", base.netloc, "ocnadefier.ro"}


def extract_links(soup: BeautifulSoup, current_url: str) -> list[str]:
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(current_url, href)
        if is_http_url(absolute):
            links.append(normalize_url(absolute))
    return sorted(set(links))


def extract_assets(soup: BeautifulSoup, current_url: str) -> list[str]:
    assets: list[str] = []
    for tag_name, attr in [("img", "src"), ("script", "src"), ("link", "href")]:
        for tag in soup.find_all(tag_name):
            value = tag.get(attr)
            if not value:
                continue
            absolute = urljoin(current_url, value.strip())
            if is_http_url(absolute):
                assets.append(normalize_url(absolute))
    return sorted(set(assets))


def assert_response_ok(response: requests.Response, url: str) -> None:
    assert response.status_code < 400, f"URL invalid: {url} -> status {response.status_code}"


@pytest.mark.parametrize("name,path", MAIN_PAGES)
def test_paginile_principale_raspund_cu_succes(session: requests.Session, name: str, path: str) -> None:
    response = get_page(session, path)
    assert_response_ok(response, make_url(path))
    assert "text/html" in response.headers.get("Content-Type", ""), f"{name} nu pare HTML"
    assert len(response.text.strip()) > 200, f"{name} pare goala sau prea scurta"


@pytest.mark.parametrize("name,path", MAIN_PAGES)
def test_paginile_principale_se_incarca_rezonabil(session: requests.Session, name: str, path: str) -> None:
    start = time.perf_counter()
    response = get_page(session, path)
    elapsed = time.perf_counter() - start
    assert_response_ok(response, make_url(path))
    assert elapsed < 10, f"{name} s-a incarcat prea greu: {elapsed:.2f}s"


def test_homepage_are_identitate_vizibila(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    visible_text = soup.get_text(" ", strip=True)
    for expected in EXPECTED_SITE_TEXT:
        assert expected in visible_text, f"Lipseste textul asteptat pe homepage: {expected}"


def test_homepage_are_meniu_principal(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    links_text = " ".join(a.get_text(" ", strip=True) for a in soup.find_all("a"))
    expected_menu_items = [
        "Istoric",
        "Cultura",
        "Geografie",
        "Obiective Turistice",
        "Lacase de cult",
        "Evenimente Locale",
        "Contact",
    ]
    for item in expected_menu_items:
        assert item.lower() in links_text.lower(), f"Lipseste item meniu: {item}"


def test_contact_are_informatii_esentiale(session: requests.Session) -> None:
    response = get_page(session, "/contact")
    soup = parse_html(response)
    text = soup.get_text(" ", strip=True)
    for expected in EXPECTED_CONTACT_TEXT:
        assert expected.lower() in text.lower(), f"Lipseste informatie contact: {expected}"
    assert re.search(r"0\d{3}[-\s]?\d{6}", text), "Nu am gasit un numar de telefon romanesc valid"
    assert re.search(r"[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}", text), "Nu am gasit email valid"


def test_monitorul_oficial_local_contine_categorii_documente(session: requests.Session) -> None:
    response = get_page(session, "/monitorul-oficial-local")
    soup = parse_html(response)
    text = soup.get_text(" ", strip=True).lower()
    expected_terms = [
        "monitorul oficial",
        "documente",
        "hotărâri",
        "dispozi",
        "autoritatea",
    ]
    missing = [term for term in expected_terms if term not in text]
    assert not missing, f"Lipsesc termeni in Monitorul Oficial Local: {missing}"


@pytest.mark.parametrize(
    "path,expected_text",
    [
        ("/istoric", "ISTORIC"),
        ("/cultura", "CULTURA"),
        ("/obiective-turistice", "OBIECTIVE TURISTICE"),
        ("/lacase-de-cult", "LACASE DE CULT"),
        ("/obiceiuri-si-traditii", "OBICEIURI SI TRADITII"),
        ("/evenimente-locale", "EVENIMENTE LOCALE"),
        ("/contact", "Contact"),
    ],
)
def test_pagini_cu_titluri_asteptate(session: requests.Session, path: str, expected_text: str) -> None:
    response = get_page(session, path)
    soup = parse_html(response)
    text = soup.get_text(" ", strip=True)
    assert expected_text.lower() in text.lower(), f"Pagina {path} nu contine titlul/textul: {expected_text}"


def test_toate_linkurile_interne_din_homepage_functioneaza(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    links = [link for link in extract_links(soup, response.url) if is_internal_url(link)]
    assert links, "Nu au fost gasite linkuri interne pe homepage"

    broken: list[str] = []
    for link in links:
        try:
            r = session.get(link, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code >= 400:
                broken.append(f"{link} -> {r.status_code}")
        except requests.RequestException as exc:
            broken.append(f"{link} -> {exc}")
    assert not broken, "Linkuri interne nefunctionale:\n" + "\n".join(broken)


def test_linkurile_externe_importante_nu_sunt_goale(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    links = [link for link in extract_links(soup, response.url) if not is_internal_url(link)]
    # Site-ul poate avea putine sau multe linkuri externe; testul verifica doar ca, daca exista, sunt URL-uri valide.
    for link in links:
        parsed = urlparse(link)
        assert parsed.scheme in {"http", "https"}
        assert parsed.netloc, f"Link extern invalid: {link}"


def test_imaginile_de_pe_homepage_au_src_valid_si_alt_recomandat(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    images = soup.find_all("img")
    assert images, "Homepage-ul nu contine imagini"

    missing_src = []
    missing_alt = []
    for index, img in enumerate(images, start=1):
        src = img.get("src")
        if not src:
            missing_src.append(str(index))
        if img.get("alt") is None:
            missing_alt.append(str(index))
    assert not missing_src, f"Imagini fara src: {missing_src}"
    # ALT este recomandare de accesibilitate; il tratam ca test strict pentru calitate.
    assert not missing_alt, f"Imagini fara atribut alt: {missing_alt}"


def test_resursele_statice_din_homepage_se_incarca(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    assets = extract_assets(soup, response.url)
    assert assets, "Nu am gasit resurse statice pe homepage"

    broken: list[str] = []
    for asset in assets[:40]:  # limita ca testul sa nu fie prea lent
        try:
            r = session.get(asset, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code >= 400:
                broken.append(f"{asset} -> {r.status_code}")
        except requests.RequestException as exc:
            broken.append(f"{asset} -> {exc}")
    assert not broken, "Resurse statice nefunctionale:\n" + "\n".join(broken)


@pytest.mark.parametrize("name,path", MAIN_PAGES)
def test_seo_title_exista_si_are_lungime_rezonabila(session: requests.Session, name: str, path: str) -> None:
    response = get_page(session, path)
    soup = parse_html(response)
    title = soup.find("title")
    assert title and title.get_text(strip=True), f"{name} nu are <title>"
    title_text = title.get_text(strip=True)
    assert 5 <= len(title_text) <= 90, f"Title nepotrivit ca lungime pentru {name}: {title_text!r}"


@pytest.mark.parametrize("name,path", MAIN_PAGES)
def test_seo_are_cel_putin_un_heading(session: requests.Session, name: str, path: str) -> None:
    response = get_page(session, path)
    soup = parse_html(response)
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    assert headings, f"{name} nu are heading-uri H1-H6"


def test_meta_description_exista_pe_homepage(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    description = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    assert description is not None, "Homepage-ul nu are meta description"
    content = description.get("content", "").strip()
    assert len(content) >= 30, "Meta description este prea scurta sau goala"


def test_nu_exista_erori_php_wordpress_vizibile(session: requests.Session) -> None:
    response = get_page(session, "/")
    text = response.text.lower()
    forbidden_fragments = [
        "fatal error",
        "warning:",
        "notice:",
        "stack trace",
        "database error",
        "error establishing a database connection",
    ]
    found = [fragment for fragment in forbidden_fragments if fragment in text]
    assert not found, f"Au fost gasite erori vizibile in pagina: {found}"


def test_https_este_folosit_si_certificatul_acceptat(session: requests.Session) -> None:
    response = session.get(BASE_URL, timeout=TIMEOUT)
    assert response.url.startswith("https://"), f"Site-ul nu foloseste HTTPS dupa redirect: {response.url}"
    assert_response_ok(response, BASE_URL)


def test_http_redirecteaza_sau_raspunde_corect(session: requests.Session) -> None:
    response = session.get("http://www.ocnadefier.ro", timeout=TIMEOUT, allow_redirects=True)
    assert_response_ok(response, "http://www.ocnadefier.ro")
    assert response.url.startswith("https://") or response.status_code == 200


def test_cautarea_exista_sau_nu_da_eroare(session: requests.Session) -> None:
    response = get_page(session, "/")
    soup = parse_html(response)
    forms = soup.find_all("form")
    search_forms = []
    for form in forms:
        form_text = str(form).lower()
        if "search" in form_text or "s=" in form_text:
            search_forms.append(form)

    # Daca exista formular de cautare, verificam cautarea fara date sensibile.
    if search_forms:
        search_response = session.get(make_url("/"), params={"s": "test"}, timeout=TIMEOUT)
        assert_response_ok(search_response, "cautare?s=test")
        assert "text/html" in search_response.headers.get("Content-Type", "")
    else:
        pytest.skip("Nu exista formular de cautare detectabil pe homepage")


def test_robots_txt_nu_da_eroare_server(session: requests.Session) -> None:
    response = session.get(urljoin(BASE_URL, "/robots.txt"), timeout=TIMEOUT)
    assert response.status_code not in {500, 502, 503, 504}, f"robots.txt da eroare server: {response.status_code}"


def test_sitemap_xml_daca_exista_este_valid(session: requests.Session) -> None:
    response = session.get(urljoin(BASE_URL, "/sitemap.xml"), timeout=TIMEOUT)
    if response.status_code == 404:
        pytest.skip("sitemap.xml nu exista")
    assert_response_ok(response, "/sitemap.xml")
    assert "<urlset" in response.text or "<sitemapindex" in response.text, "sitemap.xml nu pare valid"


# -------------------------
# Teste Selenium / browser
# -------------------------

@pytest.fixture(scope="session")
def chrome_driver():
    pytest.importorskip("selenium")
    pytest.importorskip("webdriver_manager")

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,900")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(30)
    yield driver
    driver.quit()


def test_selenium_homepage_se_incarca_in_browser(chrome_driver) -> None:
    chrome_driver.get(BASE_URL)
    assert "Ocna" in chrome_driver.title or "OCNA" in chrome_driver.page_source.upper()
    assert "COMUNA OCNA DE FIER" in chrome_driver.page_source.upper()


def test_selenium_navigare_contact(chrome_driver) -> None:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    chrome_driver.get(BASE_URL)
    wait = WebDriverWait(chrome_driver, 15)
    contact_link = wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Contact")))
    contact_link.click()
    wait.until(lambda d: "contact" in d.current_url.lower() or "CONTACT" in d.page_source.upper())
    assert "primaria@ocnadefier.ro" in chrome_driver.page_source.lower()


@pytest.mark.parametrize(
    "width,height,label",
    [
        (390, 844, "mobil"),
        (768, 1024, "tableta"),
        (1366, 900, "desktop"),
    ],
)
def test_selenium_responsive_fara_scroll_orizontal_major(chrome_driver, width: int, height: int, label: str) -> None:
    chrome_driver.set_window_size(width, height)
    chrome_driver.get(BASE_URL)
    time.sleep(1)
    scroll_width = chrome_driver.execute_script("return document.documentElement.scrollWidth")
    client_width = chrome_driver.execute_script("return document.documentElement.clientWidth")
    assert scroll_width <= client_width + 20, f"Layout-ul {label} are scroll orizontal major"


def test_selenium_contact_nu_are_erori_javascript_critice(chrome_driver) -> None:
    chrome_driver.get(make_url("/contact"))
    logs = []
    try:
        logs = chrome_driver.get_log("browser")
    except Exception:
        pytest.skip("Browser-ul nu permite citirea logurilor JS in acest mediu")

    severe_errors = [entry for entry in logs if entry.get("level") == "SEVERE"]
    assert not severe_errors, f"Erori JavaScript severe pe contact: {severe_errors}"
