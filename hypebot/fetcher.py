import logging
import httpx
from bs4 import BeautifulSoup, FeatureNotFound
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from typing import List

from . import config, state, utils


async def extract_all_images_from_page(client: httpx.AsyncClient, url: str) -> List[str]:
    images = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = await client.get(url, headers=headers, timeout=20, follow_redirects=True)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            selectors = [
                "div.gallery img",
                "div.post-gallery img",
                "div.article-gallery img",
                "div.gallery-container img",
                "figure img",
                "div.post-content img",
                "article img",
                "div[class*='gallery'] img",
                "div[class*='slider'] img",
                "div.entry-content img",
            ]
            seen_urls = set()
            for selector in selectors:
                for img in soup.select(selector):
                    img_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if not img_url:
                        continue
                    if not img_url.startswith("http"):
                        img_url = urljoin(base_url, img_url)
                    if utils.is_valid_image_url(img_url) and img_url not in seen_urls:
                        if "logo" not in img_url.lower() and "icon" not in img_url.lower():
                            images.append(img_url)
                            seen_urls.add(img_url)
                    if len(images) >= config.MAX_IMAGES_PER_POST:
                        break
                if len(images) >= config.MAX_IMAGES_PER_POST:
                    break
            logging.info(f"Найдено {len(images)} изображений на странице {url}")
    except Exception as e:
        logging.error(f"Ошибка при извлечении изображений: {e}")
    return images[: config.MAX_IMAGES_PER_POST]


async def parse_full_content(client: httpx.AsyncClient, record: dict) -> dict:
    try:
        all_images = await extract_all_images_from_page(client, record["link"])
        if all_images:
            record["images"] = all_images
            record["original_images"] = all_images.copy()
            logging.info(f"Обновлено {len(all_images)} изображений для поста {record['title'][:30]}...")
        record["needs_parsing"] = False
    except Exception as e:
        logging.error(f"Ошибка при полном парсинге: {e}")
    return record


async def fetch_releases(client: httpx.AsyncClient, progress_message=None, bot=None) -> list:
    headers = {"User-Agent": "Mozilla/5.0"}
    releases = []
    seen_titles = set()
    total_sources = len(config.SOURCES)
    for idx, src in enumerate(config.SOURCES):
        try:
            if progress_message and bot:
                try:
                    await bot.edit_message_text(
                        f"🔄 Проверяю источники... ({idx + 1}/{total_sources})\n"
                        f"📍 Сейчас: {src['name']}",
                        progress_message.chat.id,
                        progress_message.message_id,
                    )
                except Exception:
                    pass
            logging.info(f"Проверяю источник: {src['name']}")
            resp = await client.get(src["api"], headers=headers, timeout=20)
            resp.raise_for_status()
            if src["type"] == "json":
                try:
                    posts = resp.json()
                    if not isinstance(posts, list):
                        logging.warning(f"Неожиданный формат данных от {src['name']}")
                        continue
                except Exception:
                    continue
                for post in posts[:10]:
                    try:
                        link = post.get("link")
                        title_data = post.get("title", {})
                        title = (
                            title_data.get("rendered", "") if isinstance(title_data, dict) else str(title_data)
                        )
                        title = BeautifulSoup(title, "html.parser").get_text(strip=True)
                        if not link or not title or len(title) < 10:
                            continue
                        title_key = title.lower().strip()
                        if title_key in seen_titles:
                            continue
                        seen_titles.add(title_key)
                        uid = utils.make_id(src["key"], link)
                        if uid in state.state["pending"] or link in state.state["sent_links"]:
                            continue
                        date_str = post.get("date") or post.get("modified")
                        pub_date = (
                            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if date_str
                            else datetime.now(timezone.utc)
                        )
                        images = []
                        media = post.get("_embedded", {}).get("wp:featuredmedia", [])
                        if media and isinstance(media, list) and len(media) > 0:
                            featured_url = media[0].get("source_url")
                            if featured_url and utils.is_valid_image_url(featured_url):
                                images.append(featured_url)
                        context = ""
                        releases.append(
                            {
                                "id": uid,
                                "title": title[:200],
                                "link": link,
                                "images": images,
                                "original_images": images.copy(),
                                "context": context[:500] if context else "",
                                "source": src["name"],
                                "category": src.get("category", "sneakers"),
                                "timestamp": pub_date.isoformat(),
                                "needs_parsing": True,
                                "tags": utils.extract_tags(title, context),
                            }
                        )
                    except Exception:
                        continue
            elif src["type"] == "rss":
                try:
                    try:
                        soup = BeautifulSoup(resp.text, "xml")
                        items = soup.find_all("item")
                    except FeatureNotFound:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        items = soup.find_all("item")
                    if not items:
                        items = soup.find_all("entry")
                    for item in items[:10]:
                        try:
                            link = None
                            link_elem = item.find("link")
                            if link_elem:
                                link = link_elem.get_text(strip=True) if link_elem.string else link_elem.get("href")
                            if not link:
                                guid = item.find("guid")
                                if guid and guid.get_text(strip=True).startswith("http"):
                                    link = guid.get_text(strip=True)
                            title = None
                            title_elem = item.find("title")
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                            if not link or not title or len(title) < 10:
                                continue
                            title_key = title.lower().strip()
                            if title_key in seen_titles:
                                continue
                            seen_titles.add(title_key)
                            if src.get("category") == "sneakers":
                                title_lower = title.lower()
                                keywords = [
                                    "nike",
                                    "adidas",
                                    "jordan",
                                    "yeezy",
                                    "new balance",
                                    "puma",
                                    "reebok",
                                    "vans",
                                    "converse",
                                    "asics",
                                    "sneaker",
                                    "shoe",
                                    "footwear",
                                    "release",
                                    "drop",
                                    "collab",
                                    "air max",
                                    "dunk",
                                    "trainer",
                                    "runner",
                                    "retro",
                                ]
                                if not any(keyword in title_lower for keyword in keywords):
                                    continue
                            uid = utils.make_id(src["key"], link)
                            if uid in state.state["pending"] or link in state.state["sent_links"]:
                                continue
                            pub_date = utils.parse_date_from_rss(item)
                            images = []
                            description = ""
                            desc_elem = item.find("description")
                            if desc_elem:
                                desc_text = desc_elem.get_text()
                                desc_soup = BeautifulSoup(desc_text, "html.parser")
                                description = desc_soup.get_text(strip=True)[:500]
                                first_img = desc_soup.find("img", src=True)
                                if first_img:
                                    img_url = first_img.get("src")
                                    if img_url:
                                        if not img_url.startswith("http"):
                                            base_url = f"https://{urlparse(link).netloc}"
                                            img_url = urljoin(base_url, img_url)
                                        if utils.is_valid_image_url(img_url):
                                            images.append(img_url)
                            releases.append(
                                {
                                    "id": uid,
                                    "title": title[:200],
                                    "link": link,
                                    "images": images,
                                    "original_images": images.copy(),
                                    "context": description,
                                    "source": src["name"],
                                    "category": src.get("category", "sneakers"),
                                    "timestamp": pub_date.isoformat(),
                                    "needs_parsing": True,
                                    "tags": utils.extract_tags(title, description),
                                }
                            )
                        except Exception:
                            continue
                except Exception:
                    continue
        except httpx.TimeoutException:
            logging.error(f"Timeout при запросе к {src['name']}")
        except httpx.RequestError as e:
            logging.error(f"Ошибка HTTP при запросе к {src['name']}: {e}")
        except Exception as e:
            logging.error(f"Неожиданная ошибка при обработке {src['name']}: {e}")
    releases.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    logging.info(f"Найдено {len(releases)} новых релизов всего")
    return releases
