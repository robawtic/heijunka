# Database Migration Plan

This document outlines the steps to migrate from the old seeding mechanism to the new, more detailed seeding mechanism.

## Overview

The new seeding mechanism provides more realistic and detailed data for the Powertrain department, with a focus on the Shortblock group and its teams (Shortblock, Headsub, and Camsub). The data is stored in JSON files in a directory structure that mirrors the organizational hierarchy.

## Migration Steps

### 1. Backup Existing Data (Optional)

If you have valuable data in your existing database that you want to preserve, you should back it up before proceeding:

```bash
# Create a backup of the SQLite database
cp schedule.db schedule.db.backup
```

### 2. Reset the Database

The cleanest way to migrate is to reset the database and seed it from scratch:

```bash
# Run the seed_manager.py script with the --reset-db flag
python tmp_seeder_directory/seed_manager.py --department all --reset-db
```

This will drop all tables and recreate them with the new schema, then seed the database with the new data.

### 3. Generate Historical Data (Optional)

If you want to generate historical data using the new seeding mechanism:

```bash
# Run the generate_historical_data.py script with the --seed flag
python generate_historical_data.py --team headsub --seed --department powertrain --reset-db
```

This will seed the database with the new data and then generate historical data for the specified team.

## Incremental Migration (Advanced)

If you cannot reset the database, you can try an incremental migration:

1. Run the new seeding script without resetting the database:
   ```bash
   python tmp_seeder_directory/seed_manager.py --department powertrain
   ```

2. This will add new data while preserving existing data, but may result in duplicates or inconsistencies.

3. You may need to manually clean up duplicates or inconsistencies in the database.

## Verifying the Migration

After migration, you should verify that the data was seeded correctly:

1. Check that the Powertrain department and its groups and teams exist
2. Check that the workstations for each team match the JSON data
3. Check that the employees for each team match the JSON data
4. Check that the employee-workstation assignments match the JSON data

## Troubleshooting

If you encounter issues during migration:

1. Check the error messages for clues about what went wrong
2. Ensure that the JSON data files are valid and properly formatted
3. Try resetting the database and starting from scratch
4. If all else fails, restore from the backup you created in step 1