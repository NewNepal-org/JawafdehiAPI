# Permissions Model

## User Roles

### Admin
- Manage all Moderators (create, edit, delete, assign permissions)
- Manage all Contributors (create, edit, delete, assign to cases)
- Full access to all Allegations, Evidence, Sources, and Responses
- Assign Contributors to specific cases

### Moderator
- Manage Contributors (create, edit, delete, assign to cases)
- Full access to all Allegations, Evidence, Sources, and Responses
- Assign Contributors to specific cases

### Contributor
- Create new Allegations
- Access Evidence, Sources, and Responses only for assigned cases
- Edit content only for assigned cases
- Change case status only between "Draft" and "Under Review"

## Permission Matrix

| Action | Admin | Moderator | Contributor |
|--------|-------|-----------|-------------|
| Manage Moderators | ✓ | ✗ | ✗ |
| Manage Contributors | ✓ | ✓ | ✗ |
| Create Allegations | ✓ | ✓ | ✓ |
| Assign Contributors to Cases | ✓ | ✓ | ✗ |
| Access All Cases | ✓ | ✓ | ✗ |
| Access Assigned Cases | ✓ | ✓ | ✓ |
| Manage Evidence (assigned cases) | ✓ | ✓ | ✓ |
| Manage Sources (assigned cases) | ✓ | ✓ | ✓ |
| Manage Responses (assigned cases) | ✓ | ✓ | ✓ |
| Change Case Status (all statuses) | ✓ | ✓ | ✗ |
| Change Case Status (Draft ↔ Under Review) | ✓ | ✓ | ✓ |

## Case Assignment

Contributors must be explicitly assigned to cases by Admins or Moderators. Once assigned, Contributors gain access to:
- View and edit the Allegation
- Add and manage Evidence
- Document Sources
- Handle Responses

Contributors cannot access cases they are not assigned to.
