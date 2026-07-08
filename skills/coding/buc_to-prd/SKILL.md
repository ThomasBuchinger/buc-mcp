---
name: grill-to-prd
description: Turn the current conversation context into a PRD save it to docs/prds/
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

PRD naming example: `001-feature-add-basic-authentication.md` the PRD filename starts with the next number, then `feature` and a short name.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the PRD, and respect any ADRs in the area you're touching.

2. Sketch out the major modules you will need to build or modify to complete the implementation. Actively look for opportunities to extract deep modules that can be tested in isolation.

A deep module (as opposed to a shallow module) is one which encapsulates a lot of functionality in a simple, testable interface which rarely changes.

Check with the user that these modules match their expectations. Check with the user which modules they want tests written for.

3. Write the PRD using the template below, then publish it to the project issue tracker.

<prd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made.This can include:

- Existing modules/components that need to be modified
- Technical clarifications from the developer
- Architectural decisions
- Specific interactions

Use natural language, you MUST NOT include code stubs, these will be outdated very quickly

## Public Interface

Describe the **public interface** foe each component. Include important classes and functions. You **MUST NOT** include any variables or other implementation details. ONLY the name of the classes and function signatures. This is the public interface of a component, it must remain stable. Include

- Function signatures
- Class/Object names. Full defintions ony get outdated, just record the Class name
- API Contracts
- Schema Changes. Make it very clear and explicit if you change the existing schema

<public-interface-example>
```golang

struct CustomAppClient{}
func NewCustomAppClient(url string, user string, pass string) *CustomAppClient {}
func (*CustomAppClient) Login() error {}
func (*CustomAppClient) FetchData(context.Context, RequestParams) (ApiResponse, error) {}
func (*CustomAppClient) UpdateData(context.Context, RequestParams) (ApiResponse, error) {}
```
</public-interface-example>

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

Ensure you can test the user stories via the public interface. You MUST NOT rely on implementation details for testing. It makes the tests brittle

## Out of Scope

A description of the things that are out of scope for this PRD. Note anything that has beed defered to later

## Further Notes

Any further notes about the feature.

</prd-template>