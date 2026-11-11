/*Google Apps Scriptben futtatható, saját google fiókban --- engedély szükséges adott formshoz
A forms ID-t nem oszthatom meg*/

function exportFormsValaszok() {
  const FORM_ID = "ID";

  const form = FormApp.openById(FORM_ID);
  const items = form.getItems();
  const responses = form.getResponses();

  const output = SpreadsheetApp.create(
    "AI kutatás - tisztított export"
  );
  const sheet = output.getActiveSheet();

  const headers = ["Timestamp"];
  const questions = [];

  items.forEach(item => {
    const type = item.getType();
    if (
      type === FormApp.ItemType.SECTION_HEADER ||
      type === FormApp.ItemType.PAGE_BREAK ||
      type === FormApp.ItemType.IMAGE ||
      type === FormApp.ItemType.VIDEO
    ) {
      return;
    }

    const title = item.getTitle();

    if (type === FormApp.ItemType.CHECKBOX) {
      const choices = item.asCheckboxItem()
        .getChoices()
        .map(choice => choice.getValue());

      choices.forEach(choice => {
        headers.push(title + " | " + choice);
      });

      questions.push({
        id: item.getId(),
        type: "checkbox",
        choices: choices
      });

    } else if (type === FormApp.ItemType.GRID) {
      const grid = item.asGridItem();
      const gridRows = grid.getRows();

      gridRows.forEach(rowName => {
        headers.push(rowName);
      });

      questions.push({
        id: item.getId(),
        type: "grid",
        rows: gridRows
      });

    } else {
      headers.push(title);

      questions.push({
        id: item.getId(),
        type: "other"
      });
    }
  });

  const rows = [headers];

  responses.forEach(response => {
    const answerMap = new Map();

    response.getItemResponses().forEach(itemResponse => {
      answerMap.set(
        itemResponse.getItem().getId(),
        itemResponse.getResponse()
      );
    });

    const row = [response.getTimestamp()];

    questions.forEach(question => {
      const answer = answerMap.get(question.id);

      if (question.type === "checkbox") {
        const selected = Array.isArray(answer) ? answer : [];

        question.choices.forEach(choice => {
          row.push(selected.includes(choice) ? 1 : 0);
        });

      } else if (question.type === "grid") {
        const answers = Array.isArray(answer) ? answer : [];

        question.rows.forEach((_, index) => {
          row.push(answers[index] || "");
        });

      } else {
        row.push(
          answer == null ? "" :
          Array.isArray(answer) ? answer.join(" | ") :
          answer
        );
      }
    });

    rows.push(row);
  });

  if (rows.length > 1) {
    sheet.getRange(1, 1, rows.length, headers.length)
      .setValues(rows);
  } else {
    sheet.getRange(1, 1, 1, headers.length)
      .setValues([headers]);
  }

  sheet.setFrozenRows(1);

  console.log("Export elkészült:");
  console.log(output.getUrl()); /*innen manuális letöltés az url meggnyitását követően*/
  console.log("Válaszok száma: " + responses.length);
}
