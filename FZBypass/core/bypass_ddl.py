from requests import post as rpost, get as rget
from re import findall, compile, search
from time import sleep, time
from asyncio import sleep as asleep
from urllib.parse import quote, urlparse
import base64

from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from curl_cffi.requests import Session as cSession
from requests import Session, get as rget
from aiohttp import ClientSession

from FZBypass import Config
from FZBypass.core.exceptions import DDLException
from FZBypass.core.recaptcha import recaptchaV3

async def get_readable_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes}m{seconds}s"

# ==========================================
# ADVANCED GENERIC BYPASS FOR MAJOR CLONES & GADGETSWEB
# ==========================================
async def advanced_bypass(url: str) -> str:
    try:
        scraper = create_scraper(allow_brotli=False)
        domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        
        # 1. Initial GET request
        resp = scraper.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Cloudflare Check
        if soup.find('title') and 'Just a moment' in soup.find('title').text:
            raise DDLException("Bypass Failed: Cloudflare Protected / Blocked")
        
        # 2. Extract all hidden inputs
        inputs = soup.find_all("input")
        data = {inp.get("name"): inp.get("value") for inp in inputs if inp.get("name") and inp.get("value")}
        
        if data:
            await asleep(6) # Wait for potential timer
            
            # Method A: Try /links/go (Linksly / Try2Link clones)
            post_headers = {"X-Requested-With": "XMLHttpRequest", "Referer": url}
            post_resp = scraper.post(f"{domain}/links/go", data=data, headers=post_headers)
            try:
                json_data = post_resp.json()
                if "url" in json_data:
                    return json_data["url"]
            except:
                pass
            
            # Method B: Post to the same URL (Typical WP Safelink / Blogger Safelink)
            post_resp2 = scraper.post(url, data=data, headers={"Referer": url})
            soup2 = BeautifulSoup(post_resp2.text, "html.parser")
            
            # Check for redirect in the new page
            meta = soup2.find("meta", attrs={"http-equiv": "refresh"})
            if meta and "url=" in meta.get("content", "").lower():
                return meta.get("content").split("url=")[-1].strip()
                
            # Method C: Find specific anchor tags after POST
            btn = soup2.find("a", id="go-link") or soup2.find("a", class_="btn")
            if btn and btn.get("href") and btn.get("href").startswith("http"):
                return btn.get("href")
                
            # Method D: 2nd step POST (Dual page safelinks)
            inputs2 = soup2.find_all("input")
            data2 = {inp.get("name"): inp.get("value") for inp in inputs2 if inp.get("name") and inp.get("value")}
            if data2 and data2 != data:
                await asleep(5)
                post_resp3 = scraper.post(url, data=data2, headers={"Referer": url})
                soup3 = BeautifulSoup(post_resp3.text, "html.parser")
                meta3 = soup3.find("meta", attrs={"http-equiv": "refresh"})
                if meta3 and "url=" in meta3.get("content", "").lower():
                    return meta3.get("content").split("url=")[-1].strip()

        # 3. Check for meta refresh on initial page
        meta = soup.find("meta", attrs={"http-equiv": "refresh"})
        if meta and "url=" in meta.get("content", "").lower():
            return meta.get("content").split("url=")[-1].strip()

        # 4. Check for direct script redirect
        script_redirect = search(r'window\.location\.href\s*=\s*["\'](http[^"\']+)["\']', resp.text)
        if script_redirect:
            return script_redirect.group(1)

        script_redirect_2 = search(r'var\s+redirect_url\s*=\s*["\'](http[^"\']+)["\']', resp.text)
        if script_redirect_2:
            return script_redirect_2.group(1)

        # 5. Fallback to free bypass API
        try:
            api_resp = scraper.get("https://bypass.pm/bypass2", params={"url": url}).json()
            if api_resp.get("success") and api_resp.get("destination"):
                return api_resp["destination"]
        except:
            pass

        raise DDLException("No valid redirect or payload found in advanced_bypass.")
        
    except DDLException as e:
        raise e
    except Exception as e:
        raise DDLException(f"Advanced Bypass Failed: {str(e)}")

# ==========================================
# EXISTING DDL FUNCTIONS
# ==========================================

async def yandex_disk(url: str) -> str:
    cget = create_scraper().request
    try:
        return cget(
            "get",
            f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={url}",
        ).json()["href"]
    except KeyError:
        raise DDLException("File not Found / Download Limit Exceeded")

async def mediafire(url: str):
    if final_link := findall(
        r"https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+", url
    ):
        return final_link[0]
    cget = create_scraper().request
    try:
        url = cget("get", url).url
        page = cget("get", url).text
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
    if final_link := findall(
        r"\'(https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+)\'", page
    ):
        return final_link[0]
    elif temp_link := findall(
        r'\/\/(www\.mediafire\.com\/file\/\S+\/\S+\/file\?\S+)', page
    ):
        return await mediafire("https://"+temp_link[0].strip('"'))
    else:
        raise DDLException("No links found in this page")

async def shrdsk(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget("GET", url).url
        res = cget(
            "GET",
            f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}',
        )
    except Exception as e:
        raise DDLException(f"{e.__class__.__name__}")
    if res.status_code != 200:
        raise DDLException(f"Status Code {res.status_code}")
    res = res.json()
    if "type" in res and res["type"].lower() == "upload" and "video_url" in res:
        return quote(res["video_url"], safe=":/")
    raise DDLException("No Direct Link Found")

async def terabox(url: str) -> str:
    sess = Session()

    def retryme(url):
        while True:
            try:
                return sess.get(url)
            except:
                pass

    url = retryme(url).url
    key = url.split("?surl=")[-1]
    url = f"http://www.terabox.com/wap/share/filelist?surl={key}"
    sess.cookies.update({"ndus": Config.TERA_COOKIE})

    res = retryme(url)
    key = res.url.split("?surl=")[-1]
    soup = BeautifulSoup(res.content, "lxml")
    jsToken = None

    for fs in soup.find_all("script"):
        fstring = fs.string
        if fstring and fstring.startswith("try {eval(decodeURIComponent"):
            jsToken = fstring.split("%22")[1]

    res = retryme(
        f"https://www.terabox.com/share/list?app_id=250528&jsToken={jsToken}&shorturl={key}&root=1"
    )
    result = res.json()
    if result["errno"] != 0:
        raise DDLException(f"{result['errmsg']}' Check cookies")
    result = result["list"]
    if len(result) > 1:
        raise DDLException("Can't download mutiple files")
    result = result[0]

    if result["isdir"] != "0":
        raise DDLException("Can't download folder")
    try:
        return result["dlink"]
    except:
        raise DDLException("Link Extraction Failed")

async def try2link(url: str) -> str:
    DOMAIN = 'https://try2link.com'
    code = url.split('/')[-1]

    async with ClientSession() as session:
        referers = ['https://hightrip.net/', 'https://to-travel.netl', 'https://world2our.com/']
        for referer in referers:
            async with session.get(f'{DOMAIN}/{code}', headers={"Referer": referer}) as res:
                if res.status == 200:
                    html = await res.text()
                    break
        soup = BeautifulSoup(html, "html.parser")
        inputs = soup.find(id="go-link").find_all(name="input")
        data = { input.get('name'): input.get('value') for input in inputs }
        await asleep(6)
        async with session.post(f"{DOMAIN}/links/go", data=data, headers={ "X-Requested-With": "XMLHttpRequest" }) as resp:
            if 'application/json' in resp.headers.get('Content-Type'):
                json_data = await resp.json()  
                try:
                    return json_data['url']
                except:        
                    raise DDLException("Link Extraction Failed")

async def gyanilinks(url: str) -> str:
    code = url.split('/')[-1]
    useragent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    DOMAIN = "https://go.bloggingaro.com"
    
    async with ClientSession() as session:
        async with session.get(f"{DOMAIN}/{code}", headers={'Referer':'https://tech.hipsonyc.com/','User-Agent': useragent}) as res:
            cookies = res.cookies
            html = await res.text()
        async with session.get(f"{DOMAIN}/{code}", headers={'Referer':'https://hipsonyc.com/','User-Agent': useragent}, cookies=cookies) as resp:
            html = await resp.text()
        soup = BeautifulSoup(html, 'html.parser')
        data = {inp.get('name'): inp.get('value') for inp in soup.find_all('input')}
        await asleep(5)
        async with session.post(f"{DOMAIN}/links/go", data=data, headers={'X-Requested-With':'XMLHttpRequest','User-Agent': useragent, 'Referer': f"{DOMAIN}/{code}"}, cookies=cookies) as links:
            if 'application/json' in links.headers.get('Content-Type'):
                try:
                    return (await links.json())['url']
                except Exception:
                      raise DDLException("Link Extraction Failed")

async def ouo(url: str):
    tempurl = url.replace("ouo.io", "ouo.press")
    p = urlparse(tempurl)
    id = tempurl.split("/")[-1]
    client = cSession(
        headers={
            "authority": "ouo.press",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "referer": "http://www.google.com/ig/adde?moduleurl=",
            "upgrade-insecure-requests": "1",
        }
    )
    res = client.get(tempurl, impersonate="chrome110")
    next_url = f"{p.scheme}://{p.hostname}/go/{id}"

    for _ in range(2):
        if res.headers.get("Location"):
            break
        bs4 = BeautifulSoup(res.content, "lxml")
        inputs = bs4.form.findAll("input", {"name": compile(r"token$")})
        data = {inp.get("name"): inp.get("value") for inp in inputs}
        data["x-token"] = await recaptchaV3()
        res = client.post(
            next_url,
            data=data,
            headers={"content-type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
            impersonate="chrome110",
        )
        next_url = f"{p.scheme}://{p.hostname}/xreallcygo/{id}"

    return res.headers.get("Location")

async def transcript(url: str, DOMAIN: str, ref: str, sltime) -> str:
    code = url.rstrip("/").split("/")[-1]
    useragent = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'

    async with ClientSession() as session:
         async with session.get(f"{DOMAIN}/{code}", headers={'Referer': ref, 'User-Agent': useragent}) as res:
             html = await res.text()
             cookies = res.cookies
         soup = BeautifulSoup(html, "html.parser")
         title_tag = soup.find('title')
         if title_tag and title_tag.text == 'Just a moment...':
             return "Unable To Bypass Due To Cloudflare Protected"
         else:
             data = {inp.get('name'): inp.get('value') for inp in soup.find_all('input') if inp.get('name') and inp.get('value')}
             await asleep(sltime)
             async with session.post(f"{DOMAIN}/links/go", data=data, headers={'Referer': f"{DOMAIN}/{code}", 'X-Requested-With':'XMLHttpRequest', 'User-Agent': useragent}, cookies=cookies) as resp:
                  try:
                      if 'application/json' in resp.headers.get('Content-Type'):
                          return (await resp.json())['url']
                  except Exception:
                      raise DDLException("Link Extraction Failed")

async def justpaste(url: str):
    resp = rget(url, verify=False)
    soup = BeautifulSoup(resp.text, "html.parser")
    inps = soup.select('div[id="articleContent"] > p')
    return ", ".join(elem.string for elem in inps)
    
async def linksxyz(url: str):
    resp = rget(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    inps = soup.select('div[id="redirect-info"] > a')
    return inps[0]["href"]

async def shareus(url: str) -> str:
    DOMAIN = f"https://api.shrslink.xyz"
    code = url.split('/')[-1]
    headers = {
        'User-Agent':'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Origin':'https://shareus.io',
    }
    api = f"{DOMAIN}/v?shortid={code}&initial=true&referrer="
    id = rget(api, headers=headers).json()['sid']
    if id:
        api_2 = f"{DOMAIN}/get_link?sid={id}"
        res = rget(api_2, headers=headers)
        if res:
            return res.json()['link_info']['destination']
        else:
            raise DDLException("Link Extraction Failed")
    else:
        raise DDLException("ID Error")     

async def dropbox(url: str) -> str:
    return (
        url.replace("www.", "")
        .replace("dropbox.com", "dl.dropboxusercontent.com")
        .replace("?dl=0", "")
    )

async def linkvertise(url: str) -> str:
    resp = rget("https://bypass.pm/bypass2", params={"url": url}).json()
    if resp["success"]:
        return resp["destination"]
    else:
        raise DDLException(resp["msg"])

async def rslinks(url: str) -> str:
    resp = rget(url, stream=True, allow_redirects=False)
    code = resp.headers["location"].split("ms9")[-1]
    try:
        return f"http://techyproio.blogspot.com/p/short.html?{code}=="
    except:
        raise DDLException("Link Extraction Failed")

async def shorter(url: str) -> str:
    try:
        cget = create_scraper().request
        resp = cget("GET", url, allow_redirects=False)
        return resp.headers["Location"]
    except:
        raise DDLException("Link Extraction Failed")

async def appurl(url: str):
    cget = create_scraper().request
    resp = cget("GET", url, allow_redirects=False)
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.select('meta[property="og:url"]')[0]["content"]

async def surl(url: str):
    cget = create_scraper().request
    resp = cget("GET", f"{url}+")
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.select('p[class="long-url"]')[0].string.split()[1]

async def thinfi(url: str) -> str:
    try:
        return BeautifulSoup(rget(url).content, "html.parser").p.a.get("href")
    except:
        raise DDLException("Link Extraction Failed")
