def generate_prompt(answers):
    try:
        start_date = datetime.strptime(answers.get(QUESTIONS[0]["text"], "%d.%m.%Y")
        days_left = (start_date - datetime.now()).days
    except (ValueError, TypeError):
        days_left = "неизвестно (проверьте формат даты)"

    prompt = """Составь беговую программу на основе следующих ответов:

Текущий уровень подготовки: {level}
Планируемая дистанция: {distance}
До старта осталось: {days_left} дней
Доступное время на тренировки: {time_per_workout}
Количество тренировок в неделю: {workouts_per_week}
Место тренировок: {location}
Максимальная дистанция на тренировке: {max_distance} км
Ограничения по здоровью: {health_issues}
Участие в соревнованиях: {competitions}

Программа должна включать:
1. Продолжительность подготовки по неделям
2. Типы тренировок (интервальные, темповые, длинные и т.д.)
3. Рекомендации по восстановлению
4. Советы по питанию и гидратации
5. Рекомендации по экипировке
6. План на последнюю неделю перед стартом

Ответ представь в формате Markdown с четкой структурой и заголовками.""".format(
        level=answers.get(QUESTIONS[2]["text"], ""),
        distance=answers.get(QUESTIONS[1]["text"], ""),
        days_left=days_left,
        time_per_workout=answers.get(QUESTIONS[5]["text"], ""),
        workouts_per_week=answers.get(QUESTIONS[3]["text"], ""),
        location=answers.get(QUESTIONS[4]["text"], ""),
        max_distance=answers.get(QUESTIONS[7]["text"], ""),
        health_issues=answers.get(QUESTIONS[6]["text"], ""),
        competitions=answers.get(QUESTIONS[8]["text"], "")
    )
    return prompt
