---
name: swe-prd-create
description: Create documentation-first PRDs that guide development through user-facing content
user-invocable: true
---

# PRD Creation Slash Command

## Instructions

You are helping create a Product Requirements Document (PRD) for a new feature. Create a **PRD File**: Project management document with milestone tracking and implementation plan

## Process

### Step 1: Understand the Feature Concept
Ask the user to describe the feature idea to understand the core concept and scope.

### Step 2: Create PRD File with Correct Naming
Create the PRD file in: `docs/prds/feature-[feature-name].md`

### Step 3: Create PRD as a Project Management Document
Work through the PRD template focusing on project management, milestone tracking, and implementation planning. Documentation updates should be included as part of the implementation milestones.

**Key Principle**: Focus on 5-10 major milestones rather than exhaustive task lists. Each milestone should represent meaningful progress that can be clearly validated.

**Consider Including** (when applicable to the project/feature):
- **Tests** - If the project has tests, include a milestone for test coverage of new functionality
- **Documentation** - If the feature is user-facing, include a milestone for docs following existing project patterns

**Good Milestones Examples:**
- [ ] Core functionality implemented and working
- [ ] Tests passing for new functionality (if project has test suite)
- [ ] Documentation complete following existing patterns (if user-facing feature)
- [ ] Integration with existing systems working
- [ ] Feature ready for user testing

**Avoid Micro-Tasks:**
- ❌ Update README.md file
- ❌ Write test for function X
- ❌ Fix typo in documentation
- ❌ Individual file modifications

**Milestone Characteristics:**
- **Meaningful**: Represents significant progress toward completion
- **Testable**: Clear success criteria that can be validated
- **User-focused**: Relates to user value or feature capability
- **Manageable**: Can be completed in reasonable timeframe

## Discussion Guidelines

### PRD Planning Questions
1. **Problem Understanding**: "What specific problem does this feature solve for users?"
2. **User Impact**: "Walk me through the complete user journey — what will change for them?"
3. **Technical Scope**: "What are the core technical changes required?"
4. **Documentation Impact**: "Which existing docs need updates? What new docs are needed?"
5. **Integration Points**: "How does this feature integrate with existing systems?"
6. **Success Criteria**: "How will we know this feature is working well?"
7. **Implementation Phases**: "How can we deliver value incrementally?"
8. **Risk Assessment**: "What are the main risks and how do we mitigate them?"
9. **Dependencies**: "What other systems or features does this depend on?"
10. **Validation Strategy**: "How will we test and validate the implementation?"

### Discussion Tips:
- **Clarify ambiguity**: If something isn't clear, ask follow-up questions until you understand
- **Challenge assumptions**: Help the user think through edge cases, alternatives, and unintended consequences
- **Prioritize ruthlessly**: Help distinguish between must-have and nice-to-have based on user impact
- **Think about users**: Always bring the conversation back to user value, experience, and outcomes
- **Consider feasibility**: While not diving into implementation details, ensure scope is realistic
- **Focus on major milestones**: Create 5-10 meaningful milestones rather than exhaustive micro-tasks
- **Think cross-functionally**: Consider impact on different teams, systems, and stakeholders

## Workflow

1. **Concept Discussion**: Get the basic idea and validate the need
2. **Create PRD File**: Detailed document: `docs//feature-[feature-name].md`
3. **Section-by-Section Discussion**: Work through each template section systematically
4. **Milestone Definition**: Define 5-10 major milestones that represent meaningful progress
5. **Review & Validation**: Ensure completeness and clarity

## Update ROADMAP.md (If It Exists)

After creating the PRD, check if `docs/ROADMAP.md` exists. If it does, add the new feature to the appropriate timeframe section based on PRD priority:
- **High Priority** → Short-term section
- **Medium Priority** → Medium-term section
- **Low Priority** → Long-term section

Format: `- [Brief feature description] (PRD #[issue-id])`

The ROADMAP.md update will be included in the commit at the end of the workflow (Option 2).
