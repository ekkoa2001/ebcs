import { expect, test } from "@playwright/test";

test("new business modules keep the V1 shell and load real data", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("账号").fill("ekko");
  await page.getByLabel("密码").fill("123");
  await page.getByRole("button", { name: "登录工作台" }).click();
  await page.waitForSelector("[data-section='首页']");
  await expect(page.locator("body")).toHaveClass(/app-ready/);

  await expect(page.locator("#businessOverview")).toBeVisible();
  await expect(page.locator("#businessOverview .overview-stat")).toHaveCount(5);
  await expect(page.locator("#backup")).toBeHidden();
  await expect(page.locator("#restore")).toBeHidden();
  const media = await page.request.get("/api/v1/media");
  expect(media.ok()).toBeTruthy();
  const mediaRows = await media.json();
  if (mediaRows.length) {
    const preview = await page.request.get(`/api/v1/media/${mediaRows[0].id}/preview`);
    expect(preview.ok()).toBeTruthy();
    expect(preview.headers()["content-type"]).toMatch(/^image\//);
  }

  for (const name of ["品牌创意", "品牌内容", "营销方案", "售后内容", "广告复盘", "竞品洞察"]) {
    await page.getByRole("button", { name: new RegExp(name) }).click();
    if (name === "品牌创意") {
      await expect(page.locator(".business-tabs").first()).toBeVisible();
    } else if (name !== "广告复盘") {
      await expect(page.locator("#bizTitle")).toHaveText(name);
      await expect(page.locator("#bizCards")).toBeVisible();
    }
    await expect(page.locator('button.nav[aria-current="page"]')).toHaveCount(1);
  }

  await page.getByRole("button", { name: /品牌内容/ }).click();
  await expect(page.locator("#bizCompass")).toBeVisible();
  await expect(page.locator("#bizStatus")).toBeHidden();
  await expect(page.locator("#bizCompass strong").first()).toHaveCSS("color", "rgb(228, 58, 85)");
  const previewButton = page.locator(".project-preview").first();
  if (await previewButton.count()) {
    await previewButton.click();
    const gallery = page.locator("dialog.image-gallery[open]");
    await expect(gallery).toBeVisible();
    expect((await gallery.boundingBox())?.width).toBeLessThanOrEqual(930);
    await gallery.locator(".lightbox-close").click();
    await expect(page.locator("dialog.image-gallery")).toHaveCount(0);
  }
  await page.locator("#bizNew").click();
  await expect(page.locator("#bizDialogTitle")).toContainText("新建品牌内容");
  await expect(page.locator('[data-f="content_type"]')).toBeVisible();
  await expect(page.locator('.editor-section')).toHaveCount(2);
  const dateInput = page.locator('input[data-date-picker]:visible').first();
  if (await dateInput.count()) {
    await dateInput.dispatchEvent('pointerdown');
    await expect(page.locator('dialog.date-range-picker[open]')).toBeVisible();
    await expect(page.locator('.date-presets button')).toHaveCount(6);
    await page.locator('[data-date-cancel]').click();
  }
  await page.locator("#bizClose").click();
  expect(errors).toEqual([]);
});
