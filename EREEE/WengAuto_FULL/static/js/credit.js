async function calcCredit() {
  var priceEl = document.getElementById('price');
  var downEl = document.getElementById('down_payment');
  var termEl = document.getElementById('term_months');
  var rateEl = document.getElementById('rate');
  if (!priceEl) return;
  var data = {
    price: parseFloat(priceEl.value) || 0,
    down_payment: parseFloat(downEl.value) || 0,
    term_months: parseInt(termEl.value, 10) || 36,
    rate: parseFloat(rateEl.value) || 12
  };
  try {
    var resp = await fetch('/api/credit-calculator', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
      body: JSON.stringify(data),
      credentials: 'same-origin'
    });
    var result = await resp.json();
    if (result.error) {
      alert(result.error);
      return;
    }
    document.getElementById('monthly').textContent = result.monthly_payment.toLocaleString('ru-RU');
    document.getElementById('loan').textContent = result.loan_amount.toLocaleString('ru-RU');
    document.getElementById('overpay').textContent = result.overpay.toLocaleString('ru-RU');
    document.getElementById('total').textContent = result.total_payment.toLocaleString('ru-RU');
    document.getElementById('calc-result').classList.add('show');
  } catch (e) {
    alert('Ошибка расчёта. Попробуйте позже.');
  }
}
