#! /usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os

import pickle

import numpy

from time import time
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report
from imblearn.under_sampling import RandomUnderSampler
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import SGDClassifier, LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn import svm, naive_bayes
from sklearn.feature_selection import RFECV
from sklearn.cross_validation import StratifiedKFold

# import matplotlib.pyplot as plt
# import seaborn as sns
import numpy as np
import pandas as pd
import datetime

#####################################################
# GLOBAL VARIABLES

#TRAINING_DATA_ORG = "/home/zqz/Work/scholarlydata/data/training_org_features.csv"
#MODEL_NAME = "scholarlydata_org"
#TRAINING_DATA_COLS_START=3 #inclusive
#TRAINING_DATA_COLS_END=28 #exclusive
#TRAINING_DATA_COLS_FT_END=24 #exclusive
#TRAINING_DATA_COLS_TRUTH=24 #inclusive

TRAINING_DATA_ORG = "/home/zqz/Work/scholarlydata/data/training_per_features.csv"
MODEL_NAME = "scholarlydata_per"
TRAINING_DATA_COLS_START=3 #inclusive
TRAINING_DATA_COLS_END=50 #exclsive
TRAINING_DATA_COLS_FT_END=46 #exclusive
TRAINING_DATA_COLS_TRUTH=46 #inclusive

# Model selection
WITH_MultinomialNB = False
WITH_SGD = True
WITH_SLR = True
WITH_RANDOM_FOREST = False
WITH_LIBLINEAR_SVM = True
WITH_RBF_SVM = True

# Random Forest model(or any tree-based model) do not ncessarily need feature scaling
SCALING = True
# feature scaling with bound [0,1] is ncessarily for MNB model
SCALING_STRATEGY_MIN_MAX = 0
# MEAN and Standard Deviation scaling is the standard feature scaling method
SCALING_STRATEGY_MEAN_STD = 1
SCALING_STRATEGY = SCALING_STRATEGY_MEAN_STD

# DIRECTLY LOAD PRE-TRAINED MODEL FOR PREDICTION
# ENABLE THIS VARIABLE TO TEST NEW TEST SET WITHOUT TRAINING
LOAD_MODEL_FROM_FILE = False

# set automatic feature ranking and selection
AUTO_FEATURE_SELECTION = True
FEATURE_SELECTION_WITH_MAX_ENT_CLASSIFIER = False
FEATURE_SELECTION_WITH_EXTRA_TREES_CLASSIFIER = True
FEATURE_SELECTION_MANUAL_SETTING = False
# set manually selected feature index list here
# check random forest setting when changing this variable
MANUAL_SELECTED_FEATURES = []

# The number of CPUs to use to do the computation. -1 means 'all CPUs'
NUM_CPU = -1

N_FOLD_VALIDATION = 10


#####################################################


class ObjectPairClassifer(object):
    """
    supervised org/per pair classifier

    """

    def __init__(self):
        self.training_data = numpy.empty
        self.training_label = numpy.empty        

    def timestamped_print(self, msg):
        ts = str(datetime.datetime.now())
        print(ts + " :: " + msg)

    def load_training_data(self, training_file):
        df = pd.read_csv(training_file, header=0, delimiter=",", quoting=0,
                         usecols=range(TRAINING_DATA_COLS_START, TRAINING_DATA_COLS_END)).as_matrix()

        self.timestamped_print("load training data [%s] from [%s]" % (len(df), training_file))

        X, y = df[:, :TRAINING_DATA_COLS_FT_END], \
               df[:,TRAINING_DATA_COLS_TRUTH]  # X selects all rows (:), then up to columns 9; y selects all rows, and column 10 only
        self.training_data = X
        self.training_label = y

    def load_testing_data(self, testing_file):
        return pd.read_csv(testing_file, header=None, delimiter=",", quoting=0, usecols=range(0, 11)).as_matrix()

    @staticmethod
    def validate_training_set(training_set):
        """
        validate training data set (i.e., X) before scaling, PCA, etc.
        :param training_set: training set, test data
        :return:
        """
        print("np any isnan(X): ", np.any(np.isnan(training_set)))
        print("np all isfinite: ", np.all(np.isfinite(training_set)))
        # check any NaN row
        row_i = 0
        for i in training_set:
            row_i += 1
            if np.any(np.isnan(i)):
                print("ERROR: [", row_i, "] is nan: ")
                print(i)

    def feature_scaling_mean_std(self, feature_set):
        scaler = StandardScaler(with_mean=True, with_std=True)
        return scaler.fit_transform(feature_set)

    def feature_scaling_min_max(self, feature_set):
        """
        Input X must be non-negative for multinomial Naive Bayes model
        :param feature_set:
        :return:
        """
        scaler = MinMaxScaler(feature_range=(0, 1))
        return scaler.fit_transform(feature_set)

    def under_sampling(self, _X, _y):
        """
        under-sampling for unbalanced training set

        :return: X_resampled, y_resampled
        """
        rus = RandomUnderSampler()
        return rus.fit_sample(_X, _y)

    def index_max(self, values):
        return max(range(len(values)), key=values.__getitem__)

    def save_classifier_model(self, model, outfile):
        if model:
            with open(outfile, 'wb') as model_file:
                pickle.dump(model, model_file)

    def load_classifier_model(self, classifier_pickled=None):
        if classifier_pickled:
            print("Load trained model from %s", classifier_pickled)
            with open(classifier_pickled, 'rb') as model:
                classifier = pickle.load(model)
            return classifier

    def training(self):
        print("start training stage :: training data size:", len(self.training_data))
        print("train with CPU cores: [%s]" % NUM_CPU)
        # X_resampled, y_resampled = self.under_sampling(self.training_data, self.training_label)
        # Tuning hyper-parameters for precision

        # split the dataset into two parts, 0.75 for train and 0.25 for testing
        X_train, X_test, y_train, y_test = train_test_split(self.training_data, self.training_label, test_size=0.25,
                                                            random_state=0)

        ############################################################################
        #######################Multinomial Naive Bayes Model ########################
        if WITH_MultinomialNB:
            if SCALING_STRATEGY == SCALING_STRATEGY_MEAN_STD:
                print("Current scaling strategy is not suitable for MNB model. Skip ...")
            else:
                print("== Perform classification with multinomial Naive Bayes model ....")
                classifier_MNB = naive_bayes.MultinomialNB()
                tuningParams = {"alpha": [0.0001, 0.001, 0.01, 0.05, 0.1, 0.3, 0.5, 0.7, 1, 1.2, 1.5, 1.7, 2]}

                classifier_MNB = GridSearchCV(classifier_MNB, param_grid=tuningParams,
                                                        cv=N_FOLD_VALIDATION,
                                                        n_jobs=NUM_CPU)
                best_param_mnb = []
                cv_score_mnb = 0
                mnb_model_file = os.path.join(os.path.dirname(__file__), "multinomialNB-%s.m" % MODEL_NAME)
                t0 = time()
                if LOAD_MODEL_FROM_FILE:
                    print("model is loaded from [%s]" % str(mnb_model_file))
                    best_estimator = self.load_classifier_model(mnb_model_file)
                else:
                    classifier_MNB.fit(X_train, y_train)
                    best_param_mnb = classifier_MNB.best_params_
                    cv_score_mnb = classifier_MNB.best_score_
                    best_estimator = classifier_MNB.best_estimator_
                    print(
                        "Model is selected with GridSearch and trained with [%s] fold cross-validation ! " % N_FOLD_VALIDATION)

                    self.save_classifier_model(best_estimator, mnb_model_file)
                t1 = time()
                prediction_multinomialNB_dev = best_estimator.predict(X_test)
                t4 = time()

                time_multinomialNB_train = t1 - t0
                time_multinomialNB_predict_dev = t4 - t1

                print("==================== Results for MultinomialNB()")

                self.print_eval_report(best_param_mnb, cv_score_mnb,
                                       prediction_multinomialNB_dev,
                                       time_multinomialNB_predict_dev,
                                       time_multinomialNB_train, y_test)

        ######################### SGDClassifier #######################
        if WITH_SGD:
            # SGD doesn't work so well with only a few samples, but is (much more) performant with larger data
            # At n_iter=1000, SGD should converge on most datasets
            print("Perform classification with stochastic gradient descent (SGD) learning ....")
            sgd_params = {"loss": ["log", "modified_huber", "squared_hinge", 'squared_loss'],
                                 "penalty": ['l2', 'l1'],
                                 "alpha": [0.0001, 0.001, 0.01, 0.03, 0.05, 0.1],
                                 "n_iter": [1000],
                                 "learning_rate": ["optimal"]}
            classifier_sgd = SGDClassifier(loss='log', penalty='l2', n_jobs=NUM_CPU)

            classifier_sgd = GridSearchCV(classifier_sgd, param_grid=sgd_params, cv=N_FOLD_VALIDATION,
                                          n_jobs=NUM_CPU)

            best_param_sgd = []
            cv_score_sgd = 0
            sgd_model_file = os.path.join(os.path.dirname(__file__), "sgd-classifier-%s.m" % MODEL_NAME)

            t0 = time()
            if LOAD_MODEL_FROM_FILE:
                print("model is loaded from [%s]" % str(sgd_model_file))
                best_estimator = self.load_classifier_model(sgd_model_file)
            else:
                classifier_sgd.fit(X_train, y_train)
                print(
                    "Model is selected with GridSearch and trained with [%s] fold cross-validation ! " % N_FOLD_VALIDATION)
                best_estimator = classifier_sgd.best_estimator_
                self.save_classifier_model(best_estimator, sgd_model_file)
                best_param_sgd = classifier_sgd.best_params_
                cv_score_sgd = classifier_sgd.best_score_

            t1 = time()

            classes = classifier_sgd.best_estimator_.classes_
            probabilities_dev = best_estimator.predict_proba(X_test)
            prediction_sgd_dev = [classes[self.index_max(list(probs))] for probs in probabilities_dev]
            t4 = time()

            time_sgd_train = t1 - t0
            time_sgd_predict_dev = t4 - t1

            print("")
            print("\n==================== Results for stochastic gradient descent (SGD) learning ")

            self.print_eval_report(best_param_sgd, cv_score_sgd, prediction_sgd_dev,
                                   time_sgd_predict_dev,
                                   time_sgd_train, y_test)

        ######################### Stochastic Logistic Regression#######################
        if WITH_SLR:
            print("Perform classification with Stochastic Logistic Regression ....")

            slr_params = {"penalty": ['l2'],
                                 "solver": ['liblinear'],
                                 "C": list(np.power(10.0, np.arange(-10, 10))),
                                 "max_iter": [10000]}

            classifier_lr = LogisticRegression(random_state=111)
            classifier_lr = GridSearchCV(classifier_lr, param_grid=slr_params, cv=N_FOLD_VALIDATION,
                                         n_jobs=NUM_CPU)

            best_param_lr = []
            cvScores_classifier_lr = 0
            slr_model_file = os.path.join(os.path.dirname(__file__), "stochasticLR-%s.m" % MODEL_NAME)
            t0 = time()
            if LOAD_MODEL_FROM_FILE:
                print("model is loaded from [%s]" % str(slr_model_file))
                best_estimator = self.load_classifier_model(slr_model_file)
            else:
                classifier_lr.fit(X_train, y_train)

                best_param_lr = classifier_lr.best_params_
                cvScores_classifier_lr = classifier_lr.best_score_
                best_estimator = classifier_lr.best_estimator_
                print(
                    "Model is selected with GridSearch and trained with [%s] fold cross-validation ! " % N_FOLD_VALIDATION)
                self.save_classifier_model(best_estimator, slr_model_file)

            t1 = time()

            classes = best_estimator.classes_
            probabilities_dev = best_estimator.predict_proba(X_test)
            prediction_lr_dev = [classes[self.index_max(list(probs))] for probs in probabilities_dev]
            t4 = time()

            time_lr_train = t1 - t0
            time_lr_predict_dev = t4 - t1

            print("")
            print("\n==================== Results for Stochastic Logistic Regression ")

            self.print_eval_report(best_param_lr, cvScores_classifier_lr, prediction_lr_dev,
                                   time_lr_predict_dev,
                                   time_lr_train, y_test)

        ######################### Random Forest Classifier #######################
        if WITH_RANDOM_FOREST:
            print("=================Perform classification with random forest ....")
            rfc_classifier = RandomForestClassifier(n_estimators=20, n_jobs=NUM_CPU)
            # specify parameters and distributions to sample from
            rfc_tuning_params = {"max_depth": [3, 5, None],
                                 "max_features": [1, 3, 5, 7, 10],
                                 "min_samples_split": [1, 3, 10],
                                 "min_samples_leaf": [1, 3, 10],
                                 "bootstrap": [True, False],
                                 "criterion": ["gini", "entropy"]}
            rfc_classifier = GridSearchCV(rfc_classifier, param_grid=rfc_tuning_params, cv=N_FOLD_VALIDATION,
                                          n_jobs=NUM_CPU)

            best_param_rfc = []
            cv_score_rfc = 0
            best_estimator = None
            rfc_model_file = os.path.join(os.path.dirname(__file__), "random-forest_classifier-%s.m" % MODEL_NAME)

            t0 = time()
            if LOAD_MODEL_FROM_FILE:
                print("model is loaded from [%s]" % str(rfc_model_file))
                best_estimator = self.load_classifier_model(rfc_model_file)
            else:
                rfc_classifier.fit(X_train, y_train)
                print(
                    "Model is selected with GridSearch and trained with [%s] fold cross-validation ! " % N_FOLD_VALIDATION)

                best_estimator = rfc_classifier.best_estimator_
                best_param_rfc = rfc_classifier.best_params_
                cv_score_rfc = rfc_classifier.best_score_GENIA

                self.save_classifier_model(best_estimator, rfc_model_file)

            t1 = time()
            print("testing on genia development set ....")
            dev_data_prediction_rfc = best_estimator.predict(X_test)
            t4 = time()

            time_rfc_train = t1 - t0
            time_rfc_predict_dev = t4 - t1

            print("")

            print("===================== Results for Random Forest classifier ====================")
            self.print_eval_report(best_param_rfc, cv_score_rfc, dev_data_prediction_rfc,
                                   time_rfc_predict_dev,
                                   time_rfc_train, y_test)
        ####################################################################
        ############## SVM ###########################################
        #############################################################

        # Set the svm parameters by cross-validation

        tuned_parameters = [{'gamma': np.logspace(-9, 3, 3), 'probability': [True], 'C': np.logspace(-2, 10, 3)},
                            {'C': [1e-1, 1e-3, 1e-5, 0.2, 0.5, 1, 1.2, 1.3, 1.5, 1.6, 1.7, 1.8, 2]}]
        # 1e15,1e13,1e11,1e9,1e7,1e5,1e3,,

        ###################  liblinear SVM ##############################
        if WITH_LIBLINEAR_SVM:
            print("== Perform classification with liblinear SVM, kernel=linear ....")
            classifier_liblinear = svm.LinearSVC()

            classifier_liblinear = GridSearchCV(classifier_liblinear, tuned_parameters[1], cv=N_FOLD_VALIDATION,
                                                n_jobs=NUM_CPU)

            cv_score_liblinear = 0
            best_param_c_liblinear = []
            best_estimator = None
            liblinear_svm_model_file = os.path.join(os.path.dirname(__file__), "liblinear-svm-linear-%s.m" % MODEL_NAME)

            t0 = time()
            if LOAD_MODEL_FROM_FILE:
                print("model is loaded from [%s]" % str(liblinear_svm_model_file))
                best_estimator = self.load_classifier_model(liblinear_svm_model_file)
            else:
                classifier_liblinear = classifier_liblinear.fit(X_train, y_train)
                print(
                    "Model is selected with GridSearch and trained with [%s] fold cross-validation ! " % N_FOLD_VALIDATION)

                cv_score_liblinear = classifier_liblinear.best_score_
                best_param_c_liblinear = classifier_liblinear.best_params_
                best_estimator = classifier_liblinear.best_estimator_

                self.save_classifier_model(best_estimator, liblinear_svm_model_file)

            t1 = time()
            dev_data_prediction_liblinear = best_estimator.predict(X_test)
            t4 = time()

            time_liblinear_train = t1 - t0
            time_liblinear_predict_dev = t4 - t1

            print(" ==== Results for LinearSVC() =====")

            self.print_eval_report(best_param_c_liblinear, cv_score_liblinear, dev_data_prediction_liblinear,
                                   time_liblinear_predict_dev,
                                   time_liblinear_train, y_test)

        ##################### RBF svm #####################
        if WITH_RBF_SVM:
            print("== Perform classification with LinearSVC, kernel=rbf ....")
            classifier_rbf = svm.SVC()
            classifier_svc_rbf = GridSearchCV(classifier_rbf, param_grid=tuned_parameters[0], cv=N_FOLD_VALIDATION,
                                              n_jobs=NUM_CPU)
            t0 = time()

            cv_score_rbf = 0
            best_param_c_rbf = []
            best_estimator = None

            rbf_svm_model_file = os.path.join(os.path.dirname(__file__), "liblinear-svm-rbf-%s.m" % MODEL_NAME)

            if LOAD_MODEL_FROM_FILE:
                print("model is loaded from [%s]" % str(rbf_svm_model_file))
                best_estimator = self.load_classifier_model(rbf_svm_model_file)
            else:
                classifier_svc_rbf.fit(X_train, y_train)
                print(
                    "Model is selected with GridSearch and trained with [%s] fold cross-validation ! " % N_FOLD_VALIDATION)

                cv_score_rbf = classifier_svc_rbf.best_score_
                best_param_c_rbf = classifier_svc_rbf.best_params_
                best_estimator = classifier_svc_rbf.best_estimator_

                self.save_classifier_model(best_estimator, rbf_svm_model_file)

            t1 = time()
            print("testing on genia development set ....")
            dev_data_prediction_rbf = best_estimator.predict(X_test)
            t4 = time()

            time_rbf_train = t1 - t0
            time_rbf_predict_dev = t4 - t1

            print(" ==== Results for libsvm SVM (rbf) =====")

            self.print_eval_report(best_param_c_rbf, cv_score_rbf, dev_data_prediction_rbf,
                                   time_rbf_predict_dev,
                                   time_rbf_train, y_test)

        print("complete!")

    def print_eval_report(self, best_params, cv_score, prediction_dev,
                          time_predict_dev,
                          time_train, y_test):
        print("%s fold CV score [%s]; best params: [%s]" %
                         (N_FOLD_VALIDATION, cv_score, best_params))
        print("\nTraining time: %fs; "
                         "Prediction time for 'dev': %fs;" %
                         (time_train, time_predict_dev))
        print("\n %fs fold cross validation score:" % cv_score)
        print("\n----------------classification report on 25-percent dev dataset --------------")
        print("\n" + classification_report(y_test, prediction_dev))

    def feature_selection_with_max_entropy_classifier(self):
        print("automatic feature selection by maxEnt classifier ...")
        rfe = RFECV(estimator=LogisticRegression(class_weight='auto'),
                    cv=StratifiedKFold(self.training_label, 10), scoring='roc_auc', n_jobs=NUM_CPU)
        rfe.fit(self.training_data, self.training_label)

        self.training_data = rfe.transform(self.training_data)
        print("Optimal number of features : %d" % rfe.n_features_)

    def feature_selection_with_extra_tree_classifier(self):
        print("feature selection with extra tree classifier ...")
        from sklearn.ensemble import ExtraTreesClassifier
        from sklearn.feature_selection import SelectFromModel

        clf = ExtraTreesClassifier()
        clf = clf.fit(classifier.training_data, classifier.training_label)

        importances = clf.feature_importances_
        indices = np.argsort(importances)[::-1].tolist()
        model = SelectFromModel(clf, prefit=True)
        X_n = model.transform(self.training_data).shape[1]
        features_selected = indices[0:X_n]
        features_selected.sort()

        self.training_data = self.training_data[:, features_selected]

        print("Optimal number of features : %s" % str(features_selected))

    def feature_selection_with_manual_setting(self):
        print("feature selection with manual setting ...")
        if MANUAL_SELECTED_FEATURES is None or len(MANUAL_SELECTED_FEATURES) == 0:
            raise ArithmeticError("Manual selected feature is NOT set correctly!")

        self.training_data = self.training_data[:, MANUAL_SELECTED_FEATURES]

        print("Optimal number of features : %s" % str(MANUAL_SELECTED_FEATURES))


if __name__ == '__main__':
    import logging.config

    classifier = ObjectPairClassifer()

    classifier.load_training_data(TRAINING_DATA_ORG)

    classifier.validate_training_set(classifier.training_data)

    if AUTO_FEATURE_SELECTION:
        if FEATURE_SELECTION_WITH_EXTRA_TREES_CLASSIFIER:
            classifier.feature_selection_with_extra_tree_classifier()
        elif FEATURE_SELECTION_WITH_MAX_ENT_CLASSIFIER:
            classifier.feature_selection_with_max_entropy_classifier()
        elif FEATURE_SELECTION_MANUAL_SETTING:
            classifier.feature_selection_with_manual_setting()
        else:
            raise ArithmeticError("Feature selection method IS NOT SET CORRECTLY!")

    # ============== feature scaling =====================
    if SCALING:
        print("feature scaling...")
        print(" scaling method: [%s]" % SCALING_STRATEGY)

        print("example data before scaling:", classifier.training_data[0])

        if SCALING_STRATEGY == SCALING_STRATEGY_MEAN_STD:
            classifier.training_data = classifier.feature_scaling_mean_std(classifier.training_data)
        elif SCALING_STRATEGY == SCALING_STRATEGY_MIN_MAX:
            classifier.training_data = classifier.feature_scaling_min_max(classifier.training_data)
        else:
            raise ArithmeticError("SCALING STRATEGY IS NOT SET CORRECTLY!")

        print("example data after scaling:", classifier.training_data[0])
    else:
        print("training without feature scaling!")

    # ============= random sampling =================================
    print("training data size before resampling:", len(classifier.training_data))
    X_resampled, y_resampled = classifier.under_sampling(classifier.training_data,
                                                         classifier.training_label)
    print("training data size after resampling:", len(X_resampled))

    # enable this line to visualise the data
    # termClassifier.visualisation(termClassifier.training_data, termClassifier.training_label, X_resampled, y_resampled)

    classifier.training_data = X_resampled
    classifier.training_label = y_resampled

    classifier.training()
