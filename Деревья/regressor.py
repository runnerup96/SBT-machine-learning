import numpy as np
from criterion import variance, mad_median
from utils import Node

class CustomDecisionTreeRegressor:

    all_criterions = {'variance': variance, 'mad_median': mad_median}

    def __init__(self, criterion_name='variance', min_samples_leaf=1, min_samples_split=2,  max_depth=np.inf):
        """
        Дерево решений (регрессор)

        Параметры:
        ----------
        criterion_name: {"variance", "mad_median"}, default="variance"
            Критерий разделения. Поддерживаемые критерии:
            "variance" для дисперсии и "mad_median" для среднего 
            абсолютного отклонения от медианы
        min_samples_split: int, default=2
            Минимальное количество объектов, при котором будет происходить разделение узла
        min_samples_leaf: int, default=1
            Минимальное количество объектов, которые должны быть в листовом узле
        max_depth: int, default=np.inf
            Максимальная глубина дерева
        """

        assert criterion_name in self.all_criterions.keys(), \
        					'Критерий должен быть из набора: {}'.format(self.all_criterions.keys())
        
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.criterion_name = criterion_name

        self.depth = 0
        self.root = None
        
        
    def make_split(self, feature_index, threshold, X_subset, y_subset):
        """
        Выполняет разделение предоставленного подмножества данных и целевых значений с 
        использованием выбранного признака и порогового значения
        
        Параметры
        ----------
        feature_index : int
            Индекс признака для разделения
        threshold : float
            Пороговое значение для выполнения разделения
        X_subset : np.array типа float размера (n_objects, n_features)
            Матрица признаков выборки
        y_subset : np.array типа float размера (n_objects, 1)
            Вектор целевых значений
        
        Возвращает
        -------
        (X_left, y_left) : кортеж np.array того же типа, что и входные X_subset и y_subset
            Часть входной выборки, где выбранный признак x^j < порогового значения threshold
        (X_right, y_right) : кортеж np.array того же типа, что и входные X_subset и y_subset
            Часть входной выборки, где выбранный признак x^j >= порогового значения threshold
        """
        mask = X_subset[:, feature_index] >= threshold
        
        X_right = X_subset[mask]
        y_right = y_subset[mask]
        
        X_left = X_subset[~mask]
        y_left = y_subset[~mask]
        
        return (X_left, y_left), (X_right, y_right)
    
    

    def make_split_only_y(self, feature_index, threshold, X_subset, y_subset):
        """
        Разделяе целевые метки на два подмножества по указанному признаку и пороговому значению
        
        Параметры
        ----------
        feature_index : int
            Индекс признака для разделения
        threshold : float
            Пороговое значение для выполнения разделения
        X_subset : np.array типа float размера (n_objects, n_features)
            Матрица признаков выборки
        y_subset : np.array типа float размера (n_objects, 1)
            Вектор целевых значений
        
        Возвращает
        -------
        y_left : np.array типа float размера (n_objects, 1)
            Часть входной выборки, где выбранный признак x^j < порогового значения threshold
        y_right : np.array типа float размера (n_objects, 1)
            Часть входной выборки, где выбранный признак x^j >= порогового значения threshold
        """

        mask = X_subset[:, feature_index] >= threshold
        
        y_right = y_subset[mask]
        y_left = y_subset[~mask]
        
        return y_left, y_right
    


    def choose_best_split(self, X_subset, y_subset):
        """
        Жадно выбирает лучший признак и лучшее пороговое значение относительно выбранного критерия
        
        Параметры
        ----------
        X_subset : np.array типа float размера (n_objects, n_features)
            Матрица признаков, представляющая выбранное подмножество
        y_subset : np.array типа float размера (n_objects, 1)
            Вектор целевых значений
        
        Возвращает
        -------
        feature_index : int
            Индекс признака для разделения
        threshold : float
            Пороговое значение для выполнения разделения
        """

        best_gain = 0
        best_feature_index = None
        best_threshold = None

        I, N = self.criterion(y_subset), len(y_subset)
        for feature_index, x in enumerate(X_subset.T):
            x = np.sort(x)
            for threshold in x[self.min_samples_leaf:N-self.min_samples_split+1]:
                y_left, y_right = self.make_split_only_y(feature_index, threshold, X_subset, y_subset)
                I, N = self.criterion(y_subset), len(y_subset)
                I_L, N_L = self.criterion(y_left), len(y_left)
                I_R, N_R = self.criterion(y_right), len(y_right)
                gain = I - N_L/N * I_L - N_R/N * I_R
                if gain > best_gain:
                    best_gain = gain
                    best_feature_index = feature_index
                    best_threshold = threshold
                
        return best_feature_index, best_threshold
    

    
    def make_tree(self, X_subset, y_subset, curr_depth):
        """
        Рекурсивно строит дерево
        
        Параметры
        ----------
        X_subset : np.array типа float размера (n_objects, n_features)
            Матрица признаков, представляющая выбранное подмножество
        y_subset : np.array типа float размера (n_objects, 1)
            Вектор целевых значений
        curr_depth : int
        	Текущая глубина дерева
        
        Возвращает
        -------
        root_node : экземпляр класса Node
            Корень дерева
        """

        min_samples_leaf_stop = len(X_subset) < 2 * self.min_samples_leaf
        min_samples_split_stop = len(X_subset) < self.min_samples_split
        max_depth_stop = curr_depth >= self.max_depth
        criterion_stop = self.criterion(y_subset) == 0.0

        if min_samples_leaf_stop or min_samples_split_stop or max_depth_stop or criterion_stop:
            value = np.mean(y_subset) if self.criterion_name == 'variance' else np.median(y_subset)
            root_node = Node(None, value, None)

        else:
            feature_index, threshold = self.choose_best_split(X_subset, y_subset)
            if feature_index is None: # Если ни одно из разбиений не приводит к улучшению критерия создаем лист
                value = np.mean(y_subset) if self.criterion_name == 'variance' else np.median(y_subset)
                root_node = Node(None, value, None)
            else:
                (X_left, y_left), (X_right, y_right) = self.make_split(feature_index, threshold, X_subset, y_subset)
                root_node = Node(feature_index, threshold)
                self.depth = max(self.depth, curr_depth+1)
                root_node.left_child = self.make_tree(X_left, y_left, curr_depth+1)
                root_node.right_child = self.make_tree(X_right, y_right, curr_depth+1)
            
        return root_node
    
    

    def fit(self, X, y):
        """
        Строит дерево решений 
        
        Параметры
        ----------
        X : np.array типа float размера (n_objects, n_features)
            Матрица признаков, представляющая данные для обучения
        y : np.array типа float размера (n_objects, 1)
            Вектор целевых значений
        """

        assert len(y.shape) == 2 and len(y) == len(X), 'Вектор целевых значений должен быть размера (n_objects, 1)'
        self.criterion = self.all_criterions[self.criterion_name]
        self.root = self.make_tree(X, y, curr_depth=0)
        
        
        
    def predict(self, X):
        """
        Предсказывает метку класса для каждого объекта входной выборки
        
        Параметры
        ----------
        X : np.array типа float размера (n_objects, n_features)
            Матрица признаков выборки, для которой должны быть предсказаны метки классов

        Возвращает
        -------
        y_predicted : np.array типа int с формой (n_objects, 1)
            Вектор предсказанных значений
        """

        y_predicted = np.zeros(len(X))
        for i, x in enumerate(X):
            node = self.root
            while node.feature_index is not None:
                node = node.right_child if x[node.feature_index] >= node.value else node.left_child
            y_predicted[i] = node.value
        
        return y_predicted.reshape(-1, 1)