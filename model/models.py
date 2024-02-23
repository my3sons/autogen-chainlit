from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

# Pydantic Models used for extraction


class ContactType(Enum):
    Phone = 'Phone'
    Text = 'Text'


class CustomerNeed(Enum):
    """ Primary reason why the customer is calling """
    Complete_purchase_support = 'Complete purchase support'
    Technical_support = 'Technical or Product support'
    Membership_management = 'Membership management'
    Help_with_appointment_scheduling = 'Help with appointment scheduling'
    Other = 'Other'


class EmployeeResponse(Enum):
    """ How did the agent on the call ultimately help the customer """
    Fixed_or_resolved_in_the_moment = 'Fixed or resolved in the moment'
    Added_protection_plan_to_product = 'Added protection plan to product'
    Engaged_manager_or_support = 'Engaged manager or support'
    Gave_recommendation_or_advice = 'Gave recommendation or advice'
    Started_remote_support_session = 'Started remote support session'
    Unable_to_resolve_to_satisfaction = 'Unable to resolve to satisfaction'
    Canceled_membership = 'Canceled membership'
    Explained_membership_benefits = 'Explained membership benefits'
    Referred_to_other_team___unable_to_help = 'Referred to other team - unable to help'
    Renewed_membership = 'Renewed membership'
    Rescheduled_appointment = 'Rescheduled appointment'
    Other = 'Other'


class GiftCard(BaseModel):
    giftCardOffered: bool = Field(
        ...,
        description='Was a gift card offered to the customer?',
        title='Giftcardoffered',
    )
    giftCardAmount: str = Field(
        ...,
        description='Dollar amount of the gift card offered',
        title='Giftcardamount',
    )
    giftCardAccepted: bool = Field(
        ...,
        description='If gift card was offered, did the customer accept the gift card?',
        title='Giftcardaccepted',
    )


class SentimentClassifications(Enum):
    Positive = 'Positive'
    Negative = 'Negative'
    Neutral = 'Neutral'


class CustomerSentiment(BaseModel):
    sentiment: SentimentClassifications = Field(
        ..., description="Classify the customer's sentiment at the time"
    )
    reasoning: str = Field(
        ...,
        description="provide your reasoning for why you classified the customer's sentiment as you did",
        title='Reasoning',
    )


class CaseSchema(BaseModel):
    """ Information about the Customer's Case Conversation """
    summary: str = Field(
        ...,
        description='A detailed summary of the entire call transcript. Be sure to include why the customer was calling and if the customers issue was resolved and any other details that are worth mentioning. Do not use the customer or agents actual name in the summary, just refer to them as either "Agent" or "Customer"!',
        title='Summary',
    )
    orderNumber: str = Field(
        ..., description="The customer's order number", title='Ordernumber'
    )
    productSKU: str = Field(
        ...,
        description='The product SKU. The SKU is a GUID that is typically a string of digits. DO NOT assign a non-GUID value to productSKU!',
        title='Productsku',
    )
    driver: Optional[str] = Field(
        None,
        description="A name or description that could be used to identify the individual delivering and/or doing service at the customer's house",
        title='Driver',
    )
    photos: Optional[bool] = Field(
        None,
        description="where photos captured at the customer's house showing damage or product condition?",
        title='Photos',
    )
    agentCall: Optional[bool] = Field(
        None,
        description="Did the agent or delivery person make a call while at the customer's house?",
        title='Agentcall',
    )
    contactType: ContactType = Field(..., description='Contact Channel')
    productSafetyFlag: bool = Field(
        ..., description='Is there a product safety concern?', title='Productsafetyflag'
    )
    customerNeed: CustomerNeed = Field(..., title='Customer Need')
    employeeResponse: EmployeeResponse = Field(..., title='Employee Response')
    customerSentimentGoingIn: CustomerSentiment = Field(
        ...,
        description="How would you classify the customer's sentiment at the beginning of the call",
    )
    customerSentimentGoingOut: CustomerSentiment = Field(
        ...,
        description="How would you classify the customer's sentiment at the end of the call",
    )
    agentName: Optional[str] = Field(
        None, description='The name of the agent', title='Agentname'
    )
    customerName: Optional[str] = Field(
        None, description='The name of the customer', title='Customername'
    )
    giftCards: Optional[GiftCard] = Field(
        None,
        description='Were gift cards offered and if so, how much, and were they accepted by the customer?',
    )
# End Pydantic Models