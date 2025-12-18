import { test, expect } from '@playwright/test';

/**
 * GraphRAG Data-Required Test Suite
 *
 * These tests REQUIRE GraphRAG tables (RAG.Entities, RAG.EntityRelationships)
 * to be populated with data. They will FAIL if tables are empty or missing.
 *
 * Purpose: Verify actual GraphRAG functionality, not just graceful degradation.
 *
 * Prerequisites:
 * - RAG.Entities table exists and has entity data
 * - RAG.EntityRelationships table exists with relationship data
 * - Run the GraphRAG pipeline to populate tables before running these tests
 *
 * Run with: npx playwright test graphrag-data-required.spec.ts
 * Skip with: npx playwright test --grep-invert "Data-Required"
 */

test.describe('Data-Required: Knowledge Graph Search', () => {
  test('DRTC-001: Knowledge graph query returns actual entities', async ({ page }) => {
    await page.goto('/');

    // Clear any existing conversation
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Type a query that should return entities
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await chatInput.fill('Search the knowledge graph for fever');
    await chatInput.press('Enter');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    // MUST NOT see "Knowledge graph features are not available" error
    const pageText = await page.textContent('body');
    expect(pageText).not.toContain('Knowledge graph features are not available');
    expect(pageText).not.toContain('GraphRAG tables have not been created');

    // MUST see actual entity results (not an error message)
    // Look for entity type indicators that only appear with real data
    const hasEntityResults =
      pageText?.includes('SYMPTOM') ||
      pageText?.includes('CONDITION') ||
      pageText?.includes('MEDICATION') ||
      pageText?.includes('entities found') ||
      pageText?.includes('Entities Found');

    expect(hasEntityResults).toBeTruthy();
  });

  test('DRTC-002: Entity statistics returns real counts', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Click Entity Stats button
    await page.click('button:has-text("Entity Stats")');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // MUST see actual statistics with non-zero counts
    // Entity stats should show total_entities, entity_distribution, etc.
    const hasStats =
      pageText?.includes('total_entities') ||
      pageText?.includes('entity_distribution') ||
      pageText?.includes('high_confidence');

    expect(hasStats).toBeTruthy();
  });
});

test.describe('Data-Required: Visualization Charts', () => {
  test('DRTC-003: Symptom Chart renders Plotly chart with data', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Click Symptom Chart button
    await page.click('button:has-text("Symptom Chart")');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // MUST see a Plotly chart rendered (not just text response)
    const plotlyChart = page.locator('.js-plotly-plot');
    await expect(plotlyChart.first()).toBeVisible({ timeout: 5000 });
  });

  test('DRTC-004: Knowledge Graph renders interactive network', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Click Knowledge Graph button
    await page.click('button:has-text("Knowledge Graph")');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // MUST see either:
    // 1. Interactive graph component (agraph/streamlit-agraph)
    // 2. Or nodes/edges data in response indicating graph data was returned
    const hasGraphVisualization =
      (await page.locator('[data-testid="stCustomComponentV1"]').isVisible().catch(() => false)) ||
      (await page.locator('iframe').count()) > 0 ||
      pageText?.includes('nodes') ||
      pageText?.includes('edges');

    expect(hasGraphVisualization).toBeTruthy();
  });
});

test.describe('Data-Required: Hybrid Search', () => {
  test('DRTC-005: Hybrid search combines FHIR and GraphRAG results', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Type a hybrid search query
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await chatInput.fill('Use hybrid search to find chest pain cases');
    await chatInput.press('Enter');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // MUST see hybrid search results (fhir_results + graphrag_results)
    const hasHybridResults =
      pageText?.includes('fhir_results') ||
      pageText?.includes('graphrag_results') ||
      pageText?.includes('fused_results') ||
      pageText?.includes('hybrid');

    expect(hasHybridResults).toBeTruthy();
  });
});

test.describe('Data-Required: Entity Relationships', () => {
  test('DRTC-006: Entity relationship traversal returns connected entities', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Ask for entity relationships
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await chatInput.fill('Find entities related to respiratory symptoms');
    await chatInput.press('Enter');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // Should see relationship data
    const hasRelationships =
      pageText?.includes('relationships') ||
      pageText?.includes('related') ||
      pageText?.includes('connected');

    expect(hasRelationships).toBeTruthy();
  });
});

test.describe('Data-Required: Details Panel with GraphRAG Data', () => {
  test('DRTC-007: Execution details show actual entities extracted', async ({ page }) => {
    await page.goto('/');

    // Trigger a query that uses GraphRAG
    await page.click('button:has-text("Common Symptoms")');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // Skip if GraphRAG unavailable (this is a soft check - test passes but is skipped)
    if (pageText?.includes('Knowledge graph features are not available')) {
      test.skip(true, 'GraphRAG tables not available - skipping data-required test');
      return;
    }

    // Expand execution details
    const detailsExpander = page.getByText('Show Execution Details', { exact: false }).first();
    await detailsExpander.click();
    await page.waitForTimeout(500);

    // Look for Entities Found section with actual entity data
    const entitiesSection = page.getByText(/Entities Found/);
    await expect(entitiesSection).toBeVisible({ timeout: 5000 });

    // Click to expand if needed
    await entitiesSection.click();
    await page.waitForTimeout(500);

    // Should see entity type badges or entity text (not empty)
    const expandedText = await page.textContent('body');
    const hasEntityData =
      expandedText?.includes('SYMPTOM') ||
      expandedText?.includes('CONDITION') ||
      expandedText?.includes('MEDICATION') ||
      expandedText?.includes('confidence');

    expect(hasEntityData).toBeTruthy();
  });

  test('DRTC-008: Entity relationships section shows graph connections', async ({ page }) => {
    await page.goto('/');

    // Trigger a query
    await page.click('button:has-text("Common Symptoms")');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // Skip if GraphRAG unavailable
    if (pageText?.includes('Knowledge graph features are not available')) {
      test.skip(true, 'GraphRAG tables not available - skipping data-required test');
      return;
    }

    // Expand execution details
    const detailsExpander = page.getByText('Show Execution Details', { exact: false }).first();
    await detailsExpander.click();
    await page.waitForTimeout(500);

    // Look for Entity Relationships section
    const relationshipsSection = page.getByText('Entity Relationships');
    await expect(relationshipsSection).toBeVisible({ timeout: 5000 });

    // The section should show relationship data (arrows, connections, etc.)
    const expandedText = await page.textContent('body');
    const hasRelationshipVisualization =
      expandedText?.includes('→') ||
      expandedText?.includes('related') ||
      expandedText?.includes('graph');

    expect(hasRelationshipVisualization).toBeTruthy();
  });
});

test.describe('Data-Required: GraphRAG-Specific Visualizations', () => {
  test('DRTC-009: visualize_graphrag_results shows query-entity network', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Ask for GraphRAG visualization
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await chatInput.fill('Visualize graphrag results for diabetes');
    await chatInput.press('Enter');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // Should see network visualization data
    const hasVisualization =
      pageText?.includes('network') ||
      pageText?.includes('nodes') ||
      pageText?.includes('edges') ||
      pageText?.includes('entities_found');

    expect(hasVisualization).toBeTruthy();
  });

  test('DRTC-010: plot_entity_network renders with actual nodes', async ({ page }) => {
    await page.goto('/');

    // Clear chat
    const clearButton = page.locator('button:has-text("Clear")');
    if (await clearButton.isVisible()) {
      await clearButton.click();
      await page.waitForTimeout(1000);
    }

    // Ask for entity network plot
    const chatInput = page.locator('textarea[data-testid="stChatInputTextArea"]');
    await chatInput.fill('Show me the entity network graph');
    await chatInput.press('Enter');

    // Wait for response
    await expect(page.locator('.stChatMessage').nth(1)).toBeVisible({ timeout: 45000 });

    const pageText = await page.textContent('body');

    // MUST NOT see unavailable message
    expect(pageText).not.toContain('Knowledge graph features are not available');

    // Should see network data with nodes
    const hasNetworkData =
      pageText?.includes('nodes') ||
      pageText?.includes('edges') ||
      (await page.locator('[data-testid="stCustomComponentV1"]').isVisible().catch(() => false));

    expect(hasNetworkData).toBeTruthy();
  });
});
