import fs from "node:fs";
import path from "node:path";
import { expect, test, type Locator, type Page } from "@playwright/test";
import pixelmatch from "pixelmatch";
import { PNG } from "pngjs";

const baselineDir = path.resolve(__dirname, "../../docs/phase-0/screenshots");
const maxRatio = 0.002;

async function expectBaseline(page: Page, name: string, options: { fullPage?: boolean; locator?: Locator } = {}) {
  const buffer = options.locator
    ? await options.locator.screenshot()
    : await page.screenshot({ fullPage: options.fullPage ?? false });
  const actual = PNG.sync.read(buffer);
  const expected = PNG.sync.read(fs.readFileSync(path.join(baselineDir, name)));
  expect.soft(actual.width, `${name} 宽度`).toBe(expected.width);
  expect.soft(actual.height, `${name} 高度`).toBe(expected.height);
  if (actual.width !== expected.width || actual.height !== expected.height) return;
  const diff = new PNG({ width: expected.width, height: expected.height });
  const mismatched = pixelmatch(expected.data, actual.data, diff.data, expected.width, expected.height, { threshold: 0.1 });
  const ratio = mismatched / (expected.width * expected.height);
  if (ratio > maxRatio) {
    const dir = test.info().outputDir;
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${name}-diff.png`), PNG.sync.write(diff));
  }
  expect.soft(ratio, `${name} 像素差异`).toBeLessThanOrEqual(maxRatio);
}

test("V1 视觉基线", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1600);
  await expectBaseline(page, "01-login.png", { fullPage: true });

  await page.getByLabel("账号").fill("ekko");
  await page.getByLabel("密码").fill("123");
  await page.getByRole("button", { name: "登录工作台" }).click();
  await page.waitForSelector("[data-section='首页']");
  await page.waitForTimeout(800);
  await expectBaseline(page, "02-home.png", { fullPage: true });

  const openSection = async (name: string) => {
    await page.locator(`[data-section="${name}"]`).click();
    await page.waitForTimeout(500);
  };

  await openSection("开头创意");
  await expectBaseline(page, "03-hooks.png", { fullPage: true });

  await openSection("产品出场");
  await expectBaseline(page, "04-entries.png", { fullPage: true });

  await openSection("完整脚本");
  await page.waitForSelector(".storyboard-scroll");
  await expectBaseline(page, "05-scripts.png", { fullPage: true });
  await expectBaseline(page, "07-storyboard.png", { locator: page.locator(".storyboard-scroll").first() });

  await page.locator("[data-open]").first().click();
  await page.waitForSelector("dialog[open]");
  await page.waitForTimeout(400);
  await expectBaseline(page, "06-script-detail.png", { fullPage: true });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);

  await openSection("广告数据");
  await expectBaseline(page, "08-ads.png", { fullPage: true });

  await openSection("首页");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.locator("#teamNotifications").click();
  await page.waitForSelector("#eventsPanel:not([hidden])");
  await page.waitForTimeout(800);
  await expectBaseline(page, "09-activity.png", { fullPage: true });
  await page.locator("#closeEvents").click();
  await page.waitForTimeout(300);

  await page.locator("#teamAdmin").click();
  await page.waitForSelector("#workshopAdmin[open]");
  await page.waitForTimeout(800);
  await expectBaseline(page, "10-admin.png", { fullPage: true });
});
