"""Local fixture browser with real DOM interaction and no external networking."""
from pathlib import Path

def exercise(workspace,path,button_id,output_id):
    from playwright.sync_api import sync_playwright
    target=workspace.path(path)
    if target.suffix.lower() not in {".html",".htm"}:
        raise ValueError("HTML fixture required")
    # set_content does not navigate to a file origin or grant filesystem access.
    body=workspace.read(path)["text"]
    if not all(x and len(x)<=80 and x.replace("-","").replace("_","").isalnum() for x in (button_id,output_id)):
        raise ValueError("invalid element id")
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--disable-background-networking"])
        try:
            context=browser.new_context(accept_downloads=False,service_workers="block")
            context.route("**/*",lambda route:route.abort())
            context.route_web_socket("**/*",lambda socket:None)
            page=context.new_page()
            page.set_default_timeout(5000)
            page.set_content(body,wait_until="domcontentloaded",timeout=5000)
            before=page.locator("#"+output_id).inner_text()[:2000]
            page.locator("#"+button_id).click()
            after=page.locator("#"+output_id).inner_text()[:2000]
            return {"before":before,"after":after}
        finally:
            browser.close()
