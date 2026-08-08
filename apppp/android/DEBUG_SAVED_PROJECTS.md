# Saved Projects Not Displaying - Debugging Guide

## Problem Summary
Users can save projects, but when they navigate to the Projects screen, they see "No saved projects" even though projects were saved.

## Root Cause Analysis

### **Issue 1: StateFlow Subscription Timing (PRIMARY)**
**Location:** `ProjectsScreen.kt` - Line ~59
```kotlin
.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
```

**Problem:** 
- `WhileSubscribed(5000)` means the upstream Flow only collects when there are active subscribers
- If projects are saved while the ProjectsScreen is NOT visible, the upstream Flow isn't active
- The data gets inserted into the database but the StateFlow never gets notified
- When the user later navigates to ProjectsScreen and subscribes, the StateFlow emits the initial value `emptyList()` instead of querying the database for updates

**Solution Applied:**
Changed to `SharingStarted.Eagerly` which makes the StateFlow collect continuously, always staying up-to-date with database changes.

### **Issue 2: No Deletion Filter in Query (SECONDARY)**
**Location:** `ProjectDao.kt` - Line 10
```kotlin
@Query("SELECT * FROM projects WHERE isDeleted = 0 ORDER BY updatedAt DESC")
fun getAllProjects(): Flow<List<ProjectEntity>>
```

**Status:** ✅ Working correctly (projects have `isDeleted = false` by default)

---

## Fixes Applied

### 1. **Changed StateFlow Collection Strategy**
**File:** `apppp/android/app/src/main/java/com/biopolymer/screening/ui/projects/ProjectsScreen.kt`

**Before:**
```kotlin
.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
```

**After:**
```kotlin
.stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())
```

**Impact:** The StateFlow now continuously collects from the database, ensuring it always has the latest data.

### 2. **Added Comprehensive Logging**
Added logging to track:
- When projects are queried from the database
- Number of projects returned
- Individual project details (title, id, deleted flag)
- When projects are filtered and sorted
- Save operations and verification

### 3. **Added Manual Refresh Button**
- New refresh button (🔄) in the Projects screen top bar
- Manually triggers a database query to verify data exists
- Shows debug info about project count

### 4. **Added Debug Information Display**
- `debugInfo` StateFlow shows what's happening
- Call `viewModel.refreshProjects()` to trigger debug output

---

## How to Verify the Fix Works

### **Quick Test (2 minutes):**
1. Open the app and navigate to the **Screening** tab (Home)
2. Adjust some requirements and run a screening
3. Click **Save** and save the project as "Test Project"
4. You should see: ✅ "Saved successfully" toast
5. Navigate to **Projects** tab
6. **Expected:** You should see "Test Project" in the list ✅
7. If not, click the 🔄 **Refresh** button at the top

### **Debug Test (with Android Studio Logcat):**
1. Open Android Studio **Logcat**
2. Filter by `ProjectsViewModel` and `RequirementsViewModel`
3. Save a project and watch the logs:
   ```
   D/RequirementsViewModel: saveAsProject: Starting save for project 'Test'
   D/RequirementsViewModel: saveAsProject: Inserting project - id=abc-123, title=Test, isDeleted=false
   D/RequirementsViewModel: saveAsProject: Project successfully inserted into database
   D/RequirementsViewModel: saveAsProject: Verified - project exists in DB: ProjectEntity(...)
   ```
4. Navigate to Projects screen:
   ```
   D/ProjectsViewModel: Projects queried from DB: 1 items
   D/ProjectsViewModel:   - Test (id: abc-123, deleted: false)
   ```

### **Database Verification (Advanced):**
Using Android Studio Database Inspector:
1. **View** → **Tool Windows** → **Database**
2. Open `biopolymer_screening_db`
3. Go to `projects` table
4. You should see your saved projects with:
   - ✅ `isDeleted = 0` (false)
   - ✅ `title` = your project name
   - ✅ `requirementsJson` = not empty
   - ✅ `resultsJson` = not empty

---

## Key Code Locations

| Issue | File | Line | Fix |
|-------|------|------|-----|
| StateFlow Subscription | `ProjectsScreen.kt` | ~59 | Use `Eagerly` instead of `WhileSubscribed` |
| Save Verification | `RequirementsViewModel.kt` | ~180 | Added logging and verification query |
| Display Logic | `ProjectsScreen.kt` | ~200 | Shows "No saved projects" when list is empty |
| Refresh Button | `ProjectsScreen.kt` | ~155 | Manual refresh trigger |

---

## Common Issues & Solutions

### **Projects still not showing?**
1. ✅ Tap the **Refresh** button (🔄) in the Projects screen
2. ✅ Check **Logcat** for errors (see Debug Test above)
3. ✅ Verify the database using Android Studio Database Inspector
4. ✅ Try force-stopping and restarting the app

### **"No saved projects" message appears but I have saved projects**
This was the primary bug - it should now be fixed by the `SharingStarted.Eagerly` change.

### **Error: "Failed to save: ..."**
Check the error message toast for details:
- If it says "Results were null" - you must have results to save
- If it mentions JSON parsing - there's an issue with the data serialization

---

## Summary of Changes

| File | Changes | Purpose |
|------|---------|---------|
| `ProjectsScreen.kt` | StateFlow to use `Eagerly`, add logging, add refresh button | Ensure data is always current |
| `RequirementsViewModel.kt` | Add logging to save method | Verify saves complete successfully |
| `ProjectDao.kt` | No changes needed | Query is correct |
| `ProjectEntity.kt` | No changes needed | Default values are correct |

---

## Next Steps if Issue Persists

If projects still don't appear after these fixes:

1. **Check Database:**
   - Use Android Studio Database Inspector
   - Verify table exists and has data
   - Check if `isDeleted` column exists

2. **Check Logs:**
   - Look for any exceptions in Logcat
   - Check `projectDao.insertProject()` call is succeeding

3. **Check Entity Defaults:**
   - Verify `ProjectEntity` has correct default values
   - Ensure `isDeleted = false` is the default

4. **Check Query:**
   - Verify `WHERE isDeleted = 0` is correct
   - Try removing the WHERE clause temporarily to see all projects
