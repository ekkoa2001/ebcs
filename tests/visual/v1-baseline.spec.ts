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

test("current shell keeps one stable navigation", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1600);
  await expect(page.getByRole("button", { name: "登录工作台" })).toBeVisible();

  await page.getByLabel("账号").fill("ekko");
  await page.getByLabel("密码").fill("123");
  await page.getByRole("button", { name: "登录工作台" }).click();
  await expect(page.locator("button[data-section='开头创意']")).toHaveCount(0);
  for (const moduleName of ["首页", "品牌创意", "品牌内容", "营销方案", "售后内容", "广告复盘", "竞品洞察"]) {
    await page.getByRole("button", { name: moduleName, exact: true }).click();
    await page.waitForTimeout(120);
    await expect(page.locator("button.nav.active")).toHaveCount(1);
  }
  await page.getByRole("button", { name: "品牌内容", exact: true }).click();
  await expect(page.locator("#bizCards")).toBeVisible();
  await expect(page.locator(".business-workspace > .business-tools")).toBeVisible();
});
