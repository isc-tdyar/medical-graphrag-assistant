import pytest
from playwright.sync_api import expect
from tests.ux.playwright.locators import StreamlitLocators
from tests.ux.utils.streamlit_helper import wait_for_streamlit

def test_allergies_and_images_query(page, target_url):
    """
    Test the complex query 'what patients have allergies or medical images'.
    This query triggers multiple tool calls and should succeed without connection errors.
    """
    page.goto(target_url)
    wait_for_streamlit(page)
    
    query = "what patients have allergies or medical images"
    chat_input = page.locator(StreamlitLocators.CHAT_INPUT)
    chat_input.fill(query)
    chat_input.press("Enter")
    
    # Wait for assistant message to appear and have some content
    assistant_msg = page.locator(StreamlitLocators.ASSISTANT_MESSAGE).last
    assistant_msg.wait_for()
    expect(assistant_msg).not_to_have_text("", timeout=120000)
    wait_for_streamlit(page)
    
    # Verify no connection errors or missing config errors in the response
    expect(assistant_msg).not_to_contain_text("Connection error", ignore_case=True)
    expect(assistant_msg).not_to_contain_text("Configuration file not found", ignore_case=True)
    
    # Open Execution Details
    expander = page.get_by_text("Execution Details", exact=False).first
    expect(expander).to_be_visible(timeout=60000)
    expander.click()
    
    # Verify tools were executed successfully (no red X icons)
    # Streamlit renders ❌ for failed tool executions in our custom UI
    expect(expander).not_to_contain_text("❌")
    
    # Verify at least one tool was actually called
    expect(expander).to_contain_text("Tool Execution")
