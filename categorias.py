#1. Descobre as categorias que o modelo viu no treino.
#O OneHotEncoder do train.py usa handle_unknown="ignore": se mandarmos "Motorcycle" e o treino só viu "motorcycle ",
#o modelo NÃO dá erro, mas trata o valor como desconhecido e a previsão sai errada em silêncio.
def categorias_do_treino(model):
    #"pre" é o ColumnTransformer do pipeline e "cat" é o OneHotEncoder de Type_of_vehicle e Type_of_order
    pre = model.named_steps["pre"]
    encoder = pre.named_transformers_["cat"]
    colunas = [colunas for nome, _, colunas in pre.transformers_ if nome == "cat"][0]
    return dict(zip(colunas, encoder.categories_))

#2. Acha, entre as categorias do treino, a que corresponde ao valor padrão (ignora maiúsculas e espaços nas pontas)
#Se não existir, avisa quais categorias existem em vez de devolver uma previsão errada
def ajusta_categoria(model, coluna, valor):
    conhecidas = categorias_do_treino(model)[coluna]
    for categoria in conhecidas:
        if str(categoria).strip().casefold() == str(valor).strip().casefold():
            return categoria
    raise ValueError(
        f"O valor '{valor}' não existe em {coluna} no treino do modelo. "
        f"Categorias do treino: {[str(c) for c in conhecidas]}"
    )
