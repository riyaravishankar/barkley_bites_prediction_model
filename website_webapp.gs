/**
 * Barkley Bites - Website Registration Web App
 * FIX-IT-FIVE | DCP Phase 2 | Riya Ravishankar
 *
 * What this does:
 *   Receives POST requests from the Barkley Bites website's registration form
 *   and writes each submission as a new row in the Registrations tab of the
 *   Google Sheet. Includes automatic registration_id generation and basic
 *   duplicate detection by (owner_email + pet_name).
 *
 * Setup (one-time, ~5 minutes):
 *
 *   1. Open your Barkley Bites Google Sheet.
 *
 *   2. Extensions -> Apps Script. The editor opens in a new tab.
 *      If you already pasted apps_script.gs (the email alert script) into this
 *      project, that is fine. Both scripts can live in the same project.
 *
 *   3. Add a new file: click + next to "Files" -> Script. Name it
 *      "website_webapp" and paste this entire file in.
 *
 *   4. Click Save (disk icon).
 *
 *   5. Click Deploy -> New deployment.
 *      - Type:        Web app  (gear icon -> Web app)
 *      - Description: Barkley Bites registration intake v1
 *      - Execute as:  Me  (your account)
 *      - Who has access: Anyone
 *
 *      "Anyone" sounds scary but is correct - the website needs to POST
 *      without a user being logged into Google. The script itself controls
 *      what it accepts.
 *
 *   6. Click Deploy. Authorize when prompted. You will see a
 *      "This app isn't verified" page; click Advanced -> Go to {project name}
 *      (unsafe). This is normal for personal Apps Script web apps.
 *
 *   7. Copy the "Web app URL" that appears. It looks like:
 *         https://script.google.com/macros/s/AKfycb.../exec
 *      You will paste this into the website's JavaScript.
 *
 *   8. If you later change this file, you must redeploy:
 *      Deploy -> Manage deployments -> the pencil edit icon ->
 *      Version: New version -> Deploy. The URL stays the same.
 *
 * Testing without the website:
 *   Use the testRegistration() function at the bottom. In the Apps Script
 *   editor, select testRegistration from the function dropdown and click Run.
 *   It will append one test row to the Registrations tab.
 */


// ----------------------------------------------------------------------------
// Main entry point - called when the website POSTs a form submission.
// ----------------------------------------------------------------------------
function doPost(e) {
  try {
    // Parse the JSON body. The website sends Content-Type: text/plain so the
    // browser doesn't trigger a CORS preflight. The actual content is JSON.
    var data;
    try {
      data = JSON.parse(e.postData.contents);
    } catch (parseError) {
      return jsonResponse({
        success: false,
        error: "Invalid JSON body: " + parseError.toString()
      });
    }

    // Optional shared secret check - if you set SHARED_SECRET below, the
    // website must include it in the request body. Comment out the check
    // entirely if you don't want this.
    var SHARED_SECRET = "";  // e.g. "bb_2026_xyz123" - leave empty to skip
    if (SHARED_SECRET && data.secret !== SHARED_SECRET) {
      return jsonResponse({
        success: false,
        error: "Unauthorized"
      });
    }

    var sheet = SpreadsheetApp.getActiveSpreadsheet()
                  .getSheetByName("Registrations");
    if (!sheet) {
      return jsonResponse({
        success: false,
        error: "Registrations tab not found in this sheet"
      });
    }

    // Read headers so we write columns in the right order.
    var lastCol = sheet.getLastColumn();
    var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];

    // Duplicate detection: same owner_email + same pet_name within the sheet.
    var existing = sheet.getDataRange().getValues();
    var emailCol = headers.indexOf("owner_email");
    var petCol   = headers.indexOf("pet_name");
    var idCol    = headers.indexOf("registration_id");
    var breedCol = headers.indexOf("pet_breed");
    var weightCol = headers.indexOf("pet_weight_lbs");
    var bdayCol  = headers.indexOf("pet_birthday");
    var sexCol   = headers.indexOf("pet_sex");

    var isDup = "FALSE";
    var dupOf = "";
    if (existing.length > 1 && emailCol !== -1 && petCol !== -1) {
      for (var i = 1; i < existing.length; i++) {
        var sameEmail = String(existing[i][emailCol]).toLowerCase() ===
                        String(data.owner_email || "").toLowerCase();
        var samePet   = String(existing[i][petCol]).toLowerCase() ===
                        String(data.pet_name || "").toLowerCase();
        if (sameEmail && samePet) {
          dupOf = existing[i][idCol];
          // Compare attributes that, if changed, would mean "fresh registration"
          var sameAttrs =
            String(existing[i][breedCol])  === String(data.pet_breed || "") &&
            String(existing[i][weightCol]) === String(data.pet_weight_lbs || "") &&
            String(existing[i][bdayCol])   === String(data.pet_birthday || "") &&
            String(existing[i][sexCol])    === String(data.pet_sex || "");
          isDup = sameAttrs ? "TRUE" : "FALSE";
          if (!sameAttrs) dupOf = "";  // treat as fresh, no duplicate link
          break;
        }
      }
    }

    // Generate a registration ID: BB- followed by 6 uppercase chars
    var regId = "BB-" + Math.random().toString(36).slice(2, 8).toUpperCase();
    var timestamp = formatTimestamp(new Date());

    // Build the row in the order the headers appear in the sheet
    var rowByHeader = {
      registration_id:    regId,
      timestamp:          timestamp,
      owner_first_name:   data.owner_first_name || "",
      owner_last_name:    data.owner_last_name  || "",
      owner_email:        data.owner_email      || "",
      owner_phone:        data.owner_phone      || "",
      owner_city:         data.owner_city       || "",
      pet_name:           data.pet_name         || "",
      pet_breed:          data.pet_breed        || "",
      pet_birthday:       data.pet_birthday     || "",
      pet_age_years:      data.pet_age_years    || "",
      pet_weight_lbs:     data.pet_weight_lbs   || "",
      pet_sex:            data.pet_sex          || "",
      health_conditions:  data.health_conditions || "",
      signup_source:      data.signup_source    || "Website",
      n_orders:           0,
      last_order_date:    "",
      total_spend:        0,
      is_duplicate:       isDup,
      duplicate_of_id:    dupOf
    };

    var row = headers.map(function (h) {
      return rowByHeader.hasOwnProperty(h) ? rowByHeader[h] : "";
    });

    sheet.appendRow(row);

    return jsonResponse({
      success: true,
      registration_id: regId,
      is_duplicate: isDup,
      message: "Registration recorded successfully"
    });

  } catch (err) {
    // Catch-all so the website always gets a JSON response
    return jsonResponse({
      success: false,
      error: err.toString()
    });
  }
}


// ----------------------------------------------------------------------------
// Health check - the website can GET this URL to verify the endpoint is live.
// ----------------------------------------------------------------------------
function doGet(e) {
  return jsonResponse({
    success: true,
    service: "Barkley Bites Registration Intake",
    status: "live",
    timestamp: formatTimestamp(new Date())
  });
}


// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------
function jsonResponse(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function formatTimestamp(d) {
  var pad = function (n) { return n < 10 ? "0" + n : "" + n; };
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
         " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" +
         pad(d.getSeconds());
}


// ----------------------------------------------------------------------------
// Test function - run this manually from the Apps Script editor to confirm
// the script can write to the sheet without involving the website.
// ----------------------------------------------------------------------------
function testRegistration() {
  var fakePost = {
    postData: {
      contents: JSON.stringify({
        owner_first_name: "Test",
        owner_last_name:  "User",
        owner_email:      "test+" + Date.now() + "@example.com",
        owner_phone:      "555-0100",
        owner_city:       "Dallas",
        pet_name:         "TestPet",
        pet_breed:        "Labrador",
        pet_birthday:     "2023-06-15",
        pet_age_years:    "",
        pet_weight_lbs:   "62",
        pet_sex:          "Female",
        health_conditions: "",
        signup_source:    "Website"
      })
    }
  };
  var result = doPost(fakePost);
  Logger.log(result.getContent());
}
