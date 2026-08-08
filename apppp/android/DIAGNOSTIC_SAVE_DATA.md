# Comprehensive Diagnostic Guide - Saved Projects Not Displaying

## The Question: "Is data being saved or just empty space?"

This guide will help us identify **exactly where** the data is being lost.

---

## **STEP 1: Rebuild and Run the App**

Rebuild with the latest code that has enhanced logging.

---

## **STEP 2: Complete a Full Screening**

1. Go to **Screening** tab
2. Set some requirements (adjust sliders, select options)
3. Click **Run Screening** button
4. Wait for results to load
5. You should see a list of materials with scores

**Important:** The screening MUST complete successfully before you can save.

---

## **STEP 3: Try to Save**

1. On the **Results screen**, click the **Save** button
2. Enter a project name (e.g., "Test_Data_Save")
3. Click **Save**
4. Check if you see:
   - ✅ Success toast: "Saved successfully"
   - ❌ Error toast: "Failed to save: [error message]"

**If you see an error toast, share it - that's the problem!**

---

## **STEP 4: Check Logcat for Detailed Output**

Open **Android Studio** → **Logcat** tab at bottom

Filter by: `ProjectsViewModel` OR `RequirementsViewModel`

### **What to Look For When Saving:**

**Look for this pattern (successful save):**
```
D/RequirementsViewModel: saveAsProject: [1] Starting save for project 'Test_Data_Save'
D/RequirementsViewModel: saveAsProject: [2] JSON serialized:
D/RequirementsViewModel:     requirementsJson length: 2000 chars
D/RequirementsViewModel:     resultsJson length: 5000 chars
D/RequirementsViewModel: saveAsProject: [3] ProjectEntity created with full data:
D/RequirementsViewModel:     requirementsJson != null: true
D/RequirementsViewModel:     resultsJson != null: true
D/RequirementsViewModel: saveAsProject: [4] insertProject() completed
D/RequirementsViewModel: saveAsProject: [5] VERIFICATION - Project retrieved from database:
D/RequirementsViewModel:     requirementsJson length: 2000
D/RequirementsViewModel:     resultsJson length: 5000
D/RequirementsViewModel: saveAsProject: [6] Save complete - calling onSuccess()
```

### **Critical Error Messages to Look For:**

| Error | Meaning |
|-------|---------|
| `currentResults is null` | Screening didn't run or results weren't saved |
| `requirementsJson is EMPTY or NULL` | Requirements didn't serialize |
| `resultsJson is EMPTY or NULL` | **Results didn't serialize - THIS IS COMMON** |
| `Project NOT found in database after insert` | Database insert failed completely |
| `CRITICAL: resultsJson is NULL/EMPTY in database` | **Data loss - saved but with no content** |

---

## **STEP 5: Go to Projects Screen**

1. Click on **Projects** tab
2. You should see a debug card appear

### **What the Debug Card Will Show:**

#### **Case A: Database is Empty** ❌
```
Database Contents:

❌ Database is EMPTY - nothing saved!

Summary:
Total in DB: 0
Active: 0
Deleted: 0
```
**→ This means data NEVER reached the database**

#### **Case B: Data Exists in Database** ✅
```
Database Contents:

Project 1:
  Title: Test_Data_Save
  ✅ ACTIVE
  Req data: ✅ 2000b
  Res data: ✅ 5000b

Summary:
Total in DB: 1
Active: 1
Deleted: 0
```
**→ If you see this, data IS in the database but not showing in the list**

#### **Case C: Data Exists but with Empty Results** ⚠️
```
Database Contents:

Project 1:
  Title: Test_Data_Save
  ✅ ACTIVE
  Req data: ✅ 2000b
  Res data: ❌ EMPTY

Summary:
Total in DB: 1
Active: 1
Deleted: 0
```
**→ If you see this, data is partially saved but results are missing**

---

## **STEP 6: Click "Check Database" Button**

Click the blue **"Check Database"** button in the debug card.

This will:
- Query the database directly
- Show you EXACTLY what was saved
- Log detailed information to Logcat

---

## **STEP 7: Share Your Findings**

Based on the debug card output, tell us:

### **If Case A (Empty):**
```
1. Did you see "Saved successfully" toast? YES / NO
2. What does Logcat show? (paste the error)
3. Hypothesis: Data never reached database
```

### **If Case B (Data Exists with Content):**
```
1. Debug card shows: [paste what it says]
2. Hypothesis: Data is in DB but Flow isn't displaying it
3. Question: Can you see the project in the list below?
```

### **If Case C (Data Exists but Incomplete):**
```
1. Debug card shows: [paste what it says]
2. Hypothesis: Results weren't serialized properly
3. Question: When you ran screening, did it complete?
```

---

## **Most Likely Causes**

### **#1: Results are Null** (Most Common)
**Symptom:** Logcat shows "resultsJson is EMPTY or NULL"
**Cause:** Screening ran but didn't save results to ViewModel
**Check:** Does the Results screen actually show recommendations?

### **#2: Database Insert Silently Failed**
**Symptom:** Database is completely empty
**Cause:** Room database transaction failed, but no exception was thrown
**Check:** Are there any database permission errors in Logcat?

### **#3: Flow Not Emitting Updates**
**Symptom:** Data exists in database but doesn't show in list
**Cause:** StateFlow subscription issue (we already fixed this)
**Check:** Does clicking "Check Database" button make it appear?

### **#4: JSON Serialization Failed**
**Symptom:** Requirements or Results JSON is empty
**Cause:** Moshi adapter couldn't serialize the object
**Check:** Look for exception stack trace in Logcat

---

## **Next Action**

1. Save a test project
2. Go to Projects screen
3. **Screenshot the debug card** or copy the text
4. **Copy the relevant Logcat output**
5. Share both

This will tell us EXACTLY where the data is being lost!
