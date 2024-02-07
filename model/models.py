from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

# Pydantic Models used for extraction


class ContactType(Enum):
    Phone = 'Phone'
    Text = 'Text'


class CustomerNeed(Enum):
    Complete_purchase_support = 'Complete purchase support'
    Technical_support = 'Technical support'
    Membership_management = 'Membership management'
    Other = 'Other'


class EmployeeResponse(Enum):
    Added_protection_plan_to_product = 'Added protection plan to product'
    Engaged_manager_or_support = 'Engaged manager or support'
    Fixed_in_the_moment = 'Fixed in the moment'
    Gave_recommendation_or_advice = 'Gave recommendation or advice'
    Started_remote_support_session = 'Started remote support session'
    Unable_to_resolve_to_satisfaction = 'Unable to resolve to satisfaction'
    Canceled_membership = 'Canceled membership'
    Explained_membership_benefits = 'Explained membership benefits'
    Referred_to_other_team___unable_to_help = 'Referred to other team - unable to help'
    Renewed_membership = 'Renewed membership'
    Other = 'Other'


class CustomerSentimentGoingIn(Enum):
    Positive = 'Positive'
    Negative = 'Negative'
    Neutral = 'Neutral'


class CustomerSentimentGoingOut(Enum):
    Positive = 'Positive'
    Negative = 'Negative'
    Neutral = 'Neutral'


class GiftCard(BaseModel):
    giftCardOffered: bool = Field(..., title="Was a gift card offered to the customer?")
    giftCardAmount: str = Field(..., title="Dollar amount of the gift card offered")
    giftCardAccepted: bool = Field(..., title="If gift card was offered, did the customer accept the gift card?")


class CaseSchema(BaseModel):
    """ Information about the Customer's Case Conversation """
    summary: str = Field(...,
                         title='A detailed summary of the entire call transcript. Be sure to include why the customer was calling and if the customers issue was resolved, please provide those details in your summary. Do not use the customer or agents actual name in the summary, just refer to them as either "Agent" or "Customer"!')
    requiredElements: Optional[List[str]] = Field(None,
                                title="Any elements that are explicitly called out in the transcript as being required")
    orderNumber: Optional[str] = Field(None, title="The customer's order number")
    productSKU: Optional[str] = Field(None, title="The SKU associated to the product the customer might be calling about")
    driver: Optional[str] = Field(None,
                        title="A name or description that could be used to identify the individual delivering and/or doing service at the customer's house")
    photos: bool = Field(...,
                         title="where photos captured at the customer's house showing damage or product condition?")
    agentCall: bool = Field(..., title="Did the agent or delivery person make a call while at the customer's house?")
    contactType: ContactType = Field(..., title='Contact Channel')
    productSafetyFlag: bool = Field(..., title='Is there a product safety concern?')
    customerNeed: CustomerNeed = Field(..., title='Customer Need')
    employeeResponse: EmployeeResponse = Field(..., title='Employee Response')
    customerSentimentGoingIn: CustomerSentimentGoingIn = Field(...,
                                                               title="The customer's sentiment going into the conversation with agent")
    customerSentimentGoingOut: CustomerSentimentGoingOut = Field(...,
                                                                 title="The customer's sentiment at the end of the conversation with agent")
    agentName: Optional[str] = Field(None, title='The name of the agent')
    customerName: Optional[str] = Field(None, title='The name of the customer')
    giftCards: GiftCard = Field(..., title="Were gift cards offered and if so, were they accepted by the customer?")

# End Pydantic Models