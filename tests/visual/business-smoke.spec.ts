import { expect, test } from "@playwright/test";

test("new business modules keep the V1 shell and load real data", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await page.getByLabel("账号").fill("ekko");
  await page.getByLabel("密码").fill("123");
  await page.getByRole("button", { name: "登录工作台" }).click();
  await page.waitForSelector("[data-section='首页']");

  await expect(page.locator("#businessOverview")).toBeVisible();
  await expect(page.locator("#businessOverview .overview-stat")).toHaveCount(4);
  const media = await page.request.get("/api/v1/media");
  expect(media.ok()).toBeTruthy();
  const mediaRows = await media.json();
  if (mediaRows.length) {
    const preview = await page.request.get(`/api/v1/media/${mediaRows[0].id}/preview`);
    expect(preview.ok()).toBeTruthy();
    expect(preview.headers()["content-type"]).toMatch(/^image\//);
  }

  for (const name of ["品牌创意", "品牌内容", "营销方案", "竞品洞察"]) {
    await page.getByRole("button", { name: new RegExp(name) }).click();
    if (name === "品牌创意") {
      await expect(page.locator(".business-tabs").first()).toBeVisible();
    } else {
      await expect(page.locator("#bizTitle")).toHaveText(name);
      await expect(page.locator("#bizCards")).toBeVisible();
    }
  }

  await page.getByRole("button", { name: /品牌内容/ }).click();
  await page.locator("#bizNew").click();
  await expect(page.locator("#bizDialogTitle")).toContainText("新建品牌内容");
  await expect(page.locator('[data-f="content_group"]')).toBeVisible();
  await expect(page.locator('[data-f="content_type"]')).toBeVisible();
  await page.locator("#bizClose").click();

  await page.locator("#teamAdmin").click();
  await expect(page.locator("#workshopAdmin")).toBeVisible();
  await expect(page.getByRole("button", { name: "标签管理" })).toBeVisible();
  expect(errors).toEqual([]);
});
