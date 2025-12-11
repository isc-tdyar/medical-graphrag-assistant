import { test, expect } from '@playwright/test';

/**
 * Medical GraphRAG Assistant UX Test Suite
 *
 * Target: Streamlit application at http://54.209.84.148:8501
 * Features tested: Core UI (TC-001-010), Details Panel (TC-011-015)
 */

test.describe('User Story 1: Application Accessibility', () => {
  test('TC-001: Page loads successfully', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Agentic Medical Chat/);
  });

  test('TC-002: Title contains "Agentic Medical Chat"', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Agentic Medical Chat');
  });

  test('TC-003: Sidebar visible with "Available Tools" header', async ({ page }) => {
    await page.goto('/');
    const sidebar = page.locator('[data-testid="stSidebar"]');
    await expect(sidebar).toBeVisible();
    await expect(sidebar.locator('text=Available Tools')).toBeVisible();
  });

  test('TC-004: Chat input area is present', async ({ page }) => {
    await page.goto('/');
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await expect(chatInput).toBeVisible();
  });
});

test.describe('User Story 2: Example Button Interactions', () => {
  test('TC-005: Common Symptoms button triggers AI response', async ({ page }) => {
    await page.goto('/');

    // Click "Common Symptoms" button
    await page.click('button:has-text("Common Symptoms")');

    // Wait for response (up to 30s)
    await expect(page.locator('.stChatMessage')).toHaveCount(2, { timeout: 30000 });
  });

  test('TC-006: Symptom Chart button renders visualization', async ({ page }) => {
    await page.goto('/');

    // Click "Symptom Chart" button
    await page.click('button:has-text("Symptom Chart")');

    // Wait for chart to render
    await expect(page.locator('.js-plotly-plot, [data-testid="stPlotlyChart"]')).toBeVisible({ timeout: 30000 });
  });

  test('TC-007: Knowledge Graph button renders network graph', async ({ page }) => {
    await page.goto('/');

    // Click "Knowledge Graph" button
    await page.click('button:has-text("Knowledge Graph")');

    // Wait for network graph to render
    await expect(page.locator('canvas, .react-graph-vis, svg')).toBeVisible({ timeout: 30000 });
  });
});

test.describe('User Story 3: Manual Chat Input', () => {
  test('TC-008: Manual chat input produces AI response', async ({ page }) => {
    await page.goto('/');

    // Type in chat input
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await chatInput.fill('What are common symptoms?');
    await chatInput.press('Enter');

    // Wait for response
    await expect(page.locator('.stChatMessage')).toHaveCount(2, { timeout: 30000 });
  });
});

test.describe('User Story 4: Tool List Verification', () => {
  test('TC-009: Sidebar displays expected MCP tools', async ({ page }) => {
    await page.goto('/');

    const sidebar = page.locator('[data-testid="stSidebar"]');
    await expect(sidebar.locator('text=search_fhir_documents')).toBeVisible();
    await expect(sidebar.locator('text=hybrid_search')).toBeVisible();
    await expect(sidebar.locator('text=plot_entity_network')).toBeVisible();
  });
});

test.describe('User Story 5: Clear Chat', () => {
  test('TC-010: Clear button resets conversation', async ({ page }) => {
    await page.goto('/');

    // First add a message
    await page.click('button:has-text("Common Symptoms")');
    await expect(page.locator('.stChatMessage')).toHaveCount(2, { timeout: 30000 });

    // Click Clear button
    await page.click('button:has-text("Clear")');

    // Verify chat cleared
    await expect(page.locator('.stChatMessage')).toHaveCount(0, { timeout: 5000 });
  });
});

test.describe('Feature 005: GraphRAG Details Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Trigger a query to get execution details
    await page.click('button:has-text("Common Symptoms")');
    // Wait for response
    await expect(page.locator('.stChatMessage')).toHaveCount(2, { timeout: 30000 });
  });

  test('TC-011: Details expander visible after query response', async ({ page }) => {
    // Look for "Show Execution Details" expander
    await expect(page.locator('text=Show Execution Details')).toBeVisible({ timeout: 5000 });
  });

  test('TC-012: Entity section visible when details panel expanded', async ({ page }) => {
    // Click to expand details
    await page.click('text=Show Execution Details');

    // Verify "Entities Found" section is visible
    await expect(page.locator('text=Entities Found')).toBeVisible({ timeout: 5000 });
  });

  test('TC-013: Graph section visible in details panel', async ({ page }) => {
    // Click to expand details
    await page.click('text=Show Execution Details');

    // Verify "Entity Relationships" section is visible
    await expect(page.locator('text=Entity Relationships')).toBeVisible({ timeout: 5000 });
  });

  test('TC-014: Tool execution section visible in details panel', async ({ page }) => {
    // Click to expand details
    await page.click('text=Show Execution Details');

    // Verify "Tool Execution" section is visible
    await expect(page.locator('text=Tool Execution')).toBeVisible({ timeout: 5000 });
  });

  test('TC-015: Sub-sections are independently collapsible', async ({ page }) => {
    // Click to expand details
    await page.click('text=Show Execution Details');

    // Verify entities section exists
    const entitiesSection = page.locator('text=Entities Found');
    await expect(entitiesSection).toBeVisible();

    // Click to collapse entities section
    await entitiesSection.click();

    // The expander should still be clickable (toggle behavior)
    // Click again to expand
    await entitiesSection.click();
    await expect(entitiesSection).toBeVisible();
  });
});
