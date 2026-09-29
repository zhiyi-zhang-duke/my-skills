# Plan: Migrate User Data to New Schema

## Goal

We need to migrate all user data from the old `users` table to the new `users_v2` table that has a better schema. This will help with performance and let us add new features.

## Steps

1. Create the new `users_v2` table.
2. Write a migration script to copy data over.
3. Update the code to use the new table.
4. Delete the old table once everything is working.

## Timeline

We'll start this Friday and it should be done by end of next week. The migration will probably need some downtime but that should be fine.

## Notes

- The new schema uses UUIDs instead of integer IDs. We'll need to update foreign keys in other tables too but we'll figure that out as we go.
- We might want to use Redis to cache some of this data later, but that's a separate concern.
- The script will be written in Python.

